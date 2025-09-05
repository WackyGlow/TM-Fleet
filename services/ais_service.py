import socket
import threading
import traceback
from pyais import decode
from utils import AISMessageProcessor, MultipartMessageBuffer, NMEAParser
from database import AISDatabase


class AISService:
    """Service class for handling AIS message processing."""

    _instance = None

    def __init__(self, app):
        """Initialize AIS service with Flask app context."""
        self.app = app
        self.ships = {}  # Real-time ship positions
        self.ship_details = {}  # Detailed ship information

        # Initialize AIS processing components
        self.multipart_buffer = MultipartMessageBuffer()
        self.message_processor = AISMessageProcessor(
            self.ships,
            self.ship_details,
            self._get_tracked_mmsis
        )

        # Track message count for cleanup
        self.message_count = 0
        self.cleanup_timer = None

        # Start time-based position cleanup if enabled
        if self.app.config.get('ENABLE_STATUS_CLEANUP', True):
            self._start_position_cleanup_timer()

        # Store instance for singleton access
        AISService._instance = self

    @classmethod
    def get_instance(cls):
        """Get the current AIS service instance."""
        return cls._instance

    def _start_position_cleanup_timer(self):
        """Start the time-based position cleanup timer."""
        interval_minutes = self.app.config.get('STATUS_CLEANUP_INTERVAL_MINUTES', 5)

        def run_cleanup():
            try:
                underway_minutes = self.app.config.get('UNDERWAY_POSITION_TIMEOUT_MINUTES', 2)
                moored_hours = self.app.config.get('MOORED_POSITION_TIMEOUT_HOURS', 2)

                with self.app.app_context():
                    print(f"⏰ Running scheduled position cleanup...")
                    stats = AISDatabase.cleanup_old_positions_by_navigation(
                        underway_minutes=underway_minutes,
                        moored_hours=moored_hours
                    )

                    if stats.get('underway_positions_deleted', 0) > 0 or stats.get('moored_positions_deleted', 0) > 0:
                        total_deleted = stats.get('underway_positions_deleted', 0) + stats.get(
                            'moored_positions_deleted', 0)
                        print(f"✅ Scheduled cleanup removed {total_deleted} old positions")

            except Exception as e:
                print(f"❌ Error in scheduled position cleanup: {e}")
            finally:
                # Schedule next cleanup
                if self.app.config.get('ENABLE_STATUS_CLEANUP', True):
                    self._start_position_cleanup_timer()

        print(f"⏰ Scheduling position cleanup every {interval_minutes} minutes")
        self.cleanup_timer = threading.Timer(interval_minutes * 60.0, run_cleanup)
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()

    def stop_position_cleanup_timer(self):
        """Stop the position cleanup timer."""
        if self.cleanup_timer and self.cleanup_timer.is_alive():
            self.cleanup_timer.cancel()
            print("⏰ Position cleanup timer stopped")
        self.cleanup_timer = None

    def _get_tracked_mmsis(self):
        """Get current tracked MMSIs from database."""
        with self.app.app_context():
            return AISDatabase.get_tracked_mmsis()

    def start_udp_listener(self):
        """Start UDP listener for incoming AIS messages."""
        try:
            print("🚀 Starting UDP listener thread...")
            port = self.app.config['AIS_UDP_PORT']

            # Create and configure socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("📡 Created UDP socket with port reuse")

            # Bind to port
            sock.bind(("0.0.0.0", port))
            print(f"✅ UDP listener successfully bound to 0.0.0.0:{port}")
            print(f"🔍 Waiting for AIS data on port {port}...")

            # Print cleanup settings
            if self.app.config.get('ENABLE_STATUS_CLEANUP', True):
                interval_minutes = self.app.config.get('STATUS_CLEANUP_INTERVAL_MINUTES', 5)
                underway_timeout = self.app.config.get('UNDERWAY_POSITION_TIMEOUT_MINUTES', 2)
                moored_timeout = self.app.config.get('MOORED_POSITION_TIMEOUT_HOURS', 2)
                print(f"🧹 Time-based position cleanup enabled:")
                print(f"   - Cleanup interval: every {interval_minutes} minutes")
                print(f"   - Underway ships: {underway_timeout} minutes")
                print(f"   - Moored ships: {moored_timeout} hours")
            else:
                print("⚠️ Time-based position cleanup disabled")

            # Listen for messages
            while True:
                try:
                    data, addr = sock.recvfrom(8192)
                    msg = data.decode("utf-8", errors="ignore")

                    # Process each line in the message
                    for line in msg.strip().split("\n"):
                        if line.strip():
                            self._process_ais_line(line)

                except Exception as e:
                    print(f"❌ Error processing UDP message: {e}")
                    continue

        except Exception as e:
            print(f"❌ UDP listener CRITICAL ERROR: {e}")
            print("❌ Full traceback:")
            traceback.print_exc()
            raise

    def _process_ais_line(self, nmea_line):
        """Process a single AIS NMEA line."""
        try:
            line = nmea_line.strip()

            # Check if it's an AIS message
            if not NMEAParser.is_ais_message(line):
                return

            # Parse NMEA fields
            nmea_fields = NMEAParser.parse_nmea_fields(line)
            if not nmea_fields:
                return

            total_fragments = nmea_fields['total_fragments']
            fragment_number = nmea_fields['fragment_number']
            message_id = nmea_fields['message_id']
            channel = nmea_fields['channel']

            if total_fragments == 1:
                # Single part message - decode immediately
                self._decode_and_process(line)
            else:
                # Multipart message - use buffer
                complete_fragments = self.multipart_buffer.add_fragment(
                    line, total_fragments, fragment_number, message_id, channel
                )

                if complete_fragments:
                    self._decode_and_process(*complete_fragments)

            # Update message count and perform cleanup
            self._update_message_count()

        except Exception as e:
            print(f"❌ Parse error: {e}")
            print(f"Line was: {nmea_line}")

    def _decode_and_process(self, *message_lines):
        """Decode AIS message and process it."""
        try:
            decoded_message = decode(*message_lines)
            if decoded_message:
                self.message_processor.process_decoded_message(
                    decoded_message,
                    self.app.app_context
                )
        except Exception as decode_error:
            print(f"❌ Message decode error: {decode_error}")

    def _update_message_count(self):
        """Update message count and perform periodic cleanup."""
        self.message_count += 1

        cleanup_interval = self.app.config['CLEANUP_INTERVAL_MESSAGES']

        # Periodic cleanup of old fragments only
        if self.message_count % cleanup_interval == 0:
            self.multipart_buffer.cleanup_old_fragments()

    def get_stats(self):
        """Get service statistics."""
        timer_active = False
        if hasattr(self, 'cleanup_timer') and self.cleanup_timer:
            try:
                timer_active = self.cleanup_timer.is_alive()
            except (AttributeError, RuntimeError):
                timer_active = False

        return {
            "ships_count": len(self.ships),
            "details_count": len(self.ship_details),
            "message_count": self.message_count,
            "cleanup_timer_active": timer_active,
            "buffer_stats": self.multipart_buffer.get_stats()
        }