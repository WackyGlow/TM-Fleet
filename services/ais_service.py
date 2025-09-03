import socket
import traceback
from datetime import datetime, timedelta
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

        # Track cleanup statistics
        self.cleanup_stats = {
            'last_age_cleanup': None,
            'last_duplicate_cleanup': None,
            'total_age_cleanups': 0,
            'total_duplicate_cleanups': 0,
            'positions_deleted_total': 0,
            'ships_deleted_total': 0
        }

        # Track last cleanup times for time-based intervals
        self.last_age_cleanup_time = None
        self.last_duplicate_cleanup_time = None

        # Store instance for singleton access
        AISService._instance = self

    @classmethod
    def get_instance(cls):
        """Get the current AIS service instance."""
        return cls._instance

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

            # Print cleanup configuration
            if self.app.config.get('AUTO_CLEANUP_ENABLED', True):
                print(f"🧹 Automatic cleanup enabled:")
                print(
                    f"   - Position records older than {self.app.config.get('POSITION_MAX_AGE_HOURS', 2)}h will be deleted")
                print(f"   - Ship records older than {self.app.config.get('SHIP_MAX_AGE_HOURS', 24)}h will be deleted")
                print(f"   - Age-based cleanup every {self.app.config.get('AGE_CLEANUP_INTERVAL_HOURS', 1)} hours")
                print(
                    f"   - Duplicate cleanup every {self.app.config.get('DUPLICATE_CLEANUP_INTERVAL_HOURS', 6)} hours")
            else:
                print("🚫 Automatic cleanup disabled")

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
                # Trigger time-based cleanup after successful message processing
                self._trigger_automatic_cleanup()
        except Exception as decode_error:
            print(f"❌ Message decode error: {decode_error}")

    def _update_message_count(self):
        """Update message count and perform periodic cleanup of old fragments only."""
        self.message_count += 1

        cleanup_interval = self.app.config.get('CLEANUP_INTERVAL_MESSAGES', 1000)

        # Periodic cleanup of old fragments only
        if self.message_count % cleanup_interval == 0:
            self.multipart_buffer.cleanup_old_fragments()

    def _trigger_automatic_cleanup(self):
        """Trigger automatic age-based cleanup after successful AIS message processing."""
        # Check if automatic cleanup is enabled
        if not self.app.config.get('AUTO_CLEANUP_ENABLED', True):
            return

        current_time = datetime.now()

        # Get time intervals from config (in hours)
        age_cleanup_interval_hours = self.app.config.get('AGE_CLEANUP_INTERVAL_HOURS', 1.0)
        duplicate_cleanup_interval_hours = self.app.config.get('DUPLICATE_CLEANUP_INTERVAL_HOURS', 6.0)

        # Age-based cleanup - time-based
        if (self.last_age_cleanup_time is None or
                (current_time - self.last_age_cleanup_time).total_seconds() >= age_cleanup_interval_hours * 3600):
            self._perform_age_based_cleanup()
            self.last_age_cleanup_time = current_time

        # Duplicate cleanup - time-based, less frequent
        if (self.last_duplicate_cleanup_time is None or
                (
                        current_time - self.last_duplicate_cleanup_time).total_seconds() >= duplicate_cleanup_interval_hours * 3600):
            self._perform_duplicate_cleanup()
            self.last_duplicate_cleanup_time = current_time

    def _perform_age_based_cleanup(self):
        """Perform age-based cleanup of old records."""
        try:
            position_max_age = self.app.config.get('POSITION_MAX_AGE_HOURS', 2.0)
            ship_max_age = self.app.config.get('SHIP_MAX_AGE_HOURS', 24.0)

            print(f"🧹 Performing age-based cleanup (positions >{position_max_age}h, ships >{ship_max_age}h)...")

            with self.app.app_context():
                result = AISDatabase.cleanup_old_data_by_age(
                    position_hours=position_max_age,
                    ship_hours=ship_max_age
                )

                if result.get('error'):
                    print(f"❌ Age-based cleanup error: {result['error']}")
                else:
                    positions_deleted = result.get('positions_deleted', 0)
                    ships_deleted = result.get('ships_deleted', 0)

                    # Update statistics
                    self.cleanup_stats['last_age_cleanup'] = result.get('positions_cutoff')
                    self.cleanup_stats['total_age_cleanups'] += 1
                    self.cleanup_stats['positions_deleted_total'] += positions_deleted
                    self.cleanup_stats['ships_deleted_total'] += ships_deleted

                    if positions_deleted > 0 or ships_deleted > 0:
                        print(f"✅ Age-based cleanup: {positions_deleted} positions, {ships_deleted} ships deleted")

        except Exception as e:
            print(f"❌ Error during age-based cleanup: {e}")

    def _perform_duplicate_cleanup(self):
        """Perform duplicate position cleanup."""
        try:
            print(f"🧹 Performing duplicate position cleanup...")

            with self.app.app_context():
                deleted_count = AISDatabase.cleanup_old_positions()

                # Update statistics
                current_time = datetime.now()
                self.cleanup_stats['last_duplicate_cleanup'] = current_time.isoformat()
                self.cleanup_stats['total_duplicate_cleanups'] += 1

                if deleted_count > 0:
                    print(f"✅ Duplicate cleanup: {deleted_count} duplicate records removed")

        except Exception as e:
            print(f"❌ Error during duplicate cleanup: {e}")

    def get_stats(self):
        """Get service statistics."""
        return {
            "ships_count": len(self.ships),
            "details_count": len(self.ship_details),
            "message_count": self.message_count,
            "buffer_stats": self.multipart_buffer.get_stats(),
            "cleanup_stats": self.cleanup_stats.copy()
        }

    def get_cleanup_status(self):
        """Get detailed cleanup status information."""
        with self.app.app_context():
            # Get current old data stats
            position_max_age = self.app.config.get('POSITION_MAX_AGE_HOURS', 2.0)
            ship_max_age = self.app.config.get('SHIP_MAX_AGE_HOURS', 24.0)
            old_data_stats = AISDatabase.get_old_data_stats(position_max_age, ship_max_age)

            # Get duplicate stats
            duplicate_stats = AISDatabase.get_cleanup_stats()

            return {
                'auto_cleanup_enabled': self.app.config.get('AUTO_CLEANUP_ENABLED', True),
                'position_max_age_hours': position_max_age,
                'ship_max_age_hours': ship_max_age,
                'age_cleanup_interval': self.app.config.get('AGE_CLEANUP_INTERVAL_HOURS', 1.0),
                'duplicate_cleanup_interval': self.app.config.get('DUPLICATE_CLEANUP_INTERVAL_HOURS', 6.0),
                'old_data_stats': old_data_stats,
                'duplicate_stats': duplicate_stats,
                'cleanup_history': self.cleanup_stats.copy()
            }