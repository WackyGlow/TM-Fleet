import os
from flask import Flask, render_template, jsonify
import socket
import threading
from datetime import datetime
from models import db
from database import AISDatabase, AISMessageProcessor, MultipartMessageBuffer, NMEAParser

# Test pyais import
try:
    from pyais import decode

    print("✅ pyais imported successfully")
except ImportError as e:
    print(f"❌ pyais import failed: {e}")
    print("🔧 Install with: pip install pyais")
    exit(1)

# Initialize Flask app
app = Flask(__name__)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'ships.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"🔍 Database will be created at: {db_path}")

# Initialize database
db.init_app(app)
AISDatabase.init_database(app)

# Configuration
prodPort = 15100
devPort = 15200
HIGHLIGHTED_MMSIS = {"219213000", "219024900"}  # Add your own

# Shared ship data (for real-time display)
ships = {}
ship_details = {}

# Initialize services
multipart_buffer = MultipartMessageBuffer()
message_processor = AISMessageProcessor(ships, ship_details, HIGHLIGHTED_MMSIS)


def parse_ais_message(nmea_line):
    """
    Parse an AIS (Automatic Identification System) NMEA message line, handling both
    single-part and multi-part message decoding.

    This function:
    - Validates the NMEA line to ensure it's an AIS message.
    - Parses the message to extract metadata such as total fragments, fragment number,
      message ID, and channel.
    - If the message is a single-part message, it decodes and processes it immediately.
    - If the message is part of a multi-part transmission, it buffers fragments until
      the full message is assembled, then decodes and processes it.
    - Routes successfully decoded messages to the message processor for handling within
      the application context.

    Args:
        nmea_line (str): A single NMEA-formatted AIS line (e.g., starting with !AIVDM or !AIVDO).

    Returns:
        None

    Side Effects:
        - Logs any parsing or decoding errors to the console.
        - Uses the global `multipart_buffer`, `message_processor`, and Flask `app.app_context`.

    Exceptions:
        - Catches and prints exceptions related to parsing, buffering, or decoding,
          but does not raise them.
    """
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
            try:
                decoded_message = decode(line)
                if decoded_message:
                    message_processor.process_decoded_message(decoded_message, app.app_context)
            except Exception as decode_error:
                print(f"❌ Single message decode error: {decode_error}")
        else:
            # Multipart message - use buffer
            complete_fragments = multipart_buffer.add_fragment(
                line, total_fragments, fragment_number, message_id, channel
            )

            if complete_fragments:
                try:
                    # Decode the complete multipart message
                    decoded_message = decode(*complete_fragments)
                    if decoded_message:
                        message_processor.process_decoded_message(decoded_message, app.app_context)
                except Exception as decode_error:
                    print(f"❌ Multipart decode error: {decode_error}")

    except Exception as e:
        print(f"❌ Parse error: {e}")
        print(f"Line was: {nmea_line}")


def udp_listener():
    """
    Listen for incoming UDP AIS messages on the configured development port (`devPort`).

    This function performs the following:
    - Initializes a UDP socket with port reuse enabled to avoid "address already in use" errors.
    - Binds the socket to 0.0.0.0 on `devPort` to listen for messages from any IP.
    - Waits for incoming AIS data (typically from a local SDR decoder or AIS relay).
    - For each received message:
        - Splits multi-line packets and sends each line to `parse_ais_message`.
        - Tracks the number of processed messages.
        - Every 1,000 messages: performs a cleanup of stale AIS fragments from the buffer.
        - Every 10,000 messages: cleans up outdated position entries in the database (older than 7 days).

    This function runs indefinitely and is designed to be launched in a dedicated thread.

    Returns:
        None

    Side Effects:
        - Prints status and error messages to the console.
        - Triggers background cleanup tasks periodically.
        - Requires access to global objects: `multipart_buffer`, `parse_ais_message`, and `AISDatabase`.
        - Uses `app.app_context()` to access database functionality inside a Flask app context.

    Exceptions:
        - Logs and re-raises any unexpected exceptions, printing a full traceback.
    """
    try:
        print(f"🚀 Starting UDP listener thread...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Allow port reuse to avoid "address already in use" errors
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print(f"📡 Created UDP socket with port reuse")

        sock.bind(("0.0.0.0", prodPort))
        print(f"✅ UDP listener successfully bound to 0.0.0.0:{prodPort}")
        print(f"🔍 Waiting for AIS data from 10.0.16.186:{prodPort}...")

        message_count = 0
        while True:
            data, addr = sock.recvfrom(8192)
            msg = data.decode("utf-8", errors="ignore")

            for line in msg.strip().split("\n"):
                if line.strip():
                    parse_ais_message(line)
                    message_count += 1

                    # Periodic cleanup of old fragments
                    if message_count % 1000 == 0:
                        multipart_buffer.cleanup_old_fragments()

                        # Cleanup old database positions every 10k messages
                        if message_count % 10000 == 0:
                            with app.app_context():
                                AISDatabase.cleanup_old_positions(days=7)

    except Exception as e:
        print(f"❌ UDP listener CRITICAL ERROR: {e}")
        import traceback
        print("❌ Full traceback:")
        traceback.print_exc()
        raise


# Flask Routes
@app.route("/")
def index():
    return render_template("map.html")


@app.route("/ships")
def get_ships():
    """Return ship data for the frontend (real-time memory data)."""
    return jsonify({
        "ships": ships,
        "highlighted": list(HIGHLIGHTED_MMSIS),
        "details": ship_details
    })


@app.route("/debug")
def debug():
    """Debug endpoint to see raw data."""
    db_stats = AISDatabase.get_database_stats()
    buffer_stats = multipart_buffer.get_stats()

    return jsonify({
        "ships_count": len(ships),
        "ships": ships,
        "details": ship_details,
        "multipart_buffer": buffer_stats,
        "database_stats": db_stats
    })


@app.route("/db/ships")
def get_db_ships():
    """Get recent ships from database."""
    recent_ships = AISDatabase.get_recent_ships(hours=24)
    return jsonify({"ships": recent_ships})


@app.route("/db/ship/<mmsi>")
def get_ship_info(mmsi):
    """Get detailed information for a specific ship."""
    ship_details_db = AISDatabase.get_ship_details(mmsi)
    ship_track = AISDatabase.get_ship_track(mmsi, hours=24)

    return jsonify({
        "ship": ship_details_db,
        "track": ship_track
    })


@app.route("/db/stats")
def get_db_stats():
    """Get database statistics."""
    return jsonify(AISDatabase.get_database_stats())


@app.route("/db/cleanup")
def cleanup_database():
    """Manual database cleanup endpoint."""
    deleted_count = AISDatabase.cleanup_old_positions(days=7)
    return jsonify({
        "message": "Database cleanup completed",
        "deleted_positions": deleted_count
    })


if __name__ == "__main__":
    """
        Entry point for the AIS tracking application.

        This block:
        - Starts a test thread to verify threading is working.
        - Initializes and starts the UDP listener in a daemon thread.
        - Waits briefly to ensure the listener has time to start.
        - Starts the Flask web server for the frontend and API routes.

        Notes:
        - The UDP listener thread runs in the background and processes incoming AIS messages.
        - Flask is started with `use_reloader=False` to avoid double-threading issues during development.
        - The main thread monitors the health of the UDP listener before launching Flask.
    """
    print(f"🎯 MAIN: Starting AIS tracking application...")


    # Test thread creation
    def test_thread():
        print("🧪 TEST: Thread is working!")


    test_t = threading.Thread(target=test_thread)
    test_t.start()
    test_t.join()

    print(f"📦 MAIN: Creating UDP listener thread...")

    # Start UDP listener thread
    t = threading.Thread(target=udp_listener, daemon=True)
    print(f"🚀 MAIN: Starting UDP listener thread...")
    t.start()

    # Give thread time to start
    import time

    time.sleep(2)

    print(f"🌐 MAIN: Starting Flask app...")
    print(f"📡 MAIN: UDP should be listening on port {prodPort}")

    if t.is_alive():
        print("✅ MAIN: UDP listener thread is running")
    else:
        print("❌ MAIN: UDP listener thread DIED!")

    # Disable Flask's reloader to prevent double initialization
    app.run(host="0.0.0.0", debug=False, use_reloader=False)