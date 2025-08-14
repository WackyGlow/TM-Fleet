import os
import socket
import threading
import time
from flask import Flask

# Import configuration and services
from config import Config
from services.ais_service import AISService
from routes import register_routes
from models import db
from database import AISDatabase


def create_app():
    """Flask application factory."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)
    AISDatabase.init_database(app)

    # Register routes
    register_routes(app)

    return app


def main():
    """Main application entry point."""
    print("🎯 MAIN: Starting SpyFleet AIS tracking application...")

    # Test threading
    test_threading()

    # Create Flask app
    app = create_app()

    # Initialize AIS service
    ais_service = AISService(app)

    # Start UDP listener in background
    start_udp_listener(ais_service)

    # Start Flask web server
    start_web_server(app)


def test_threading():
    """Test that threading is working correctly."""

    def test_thread():
        print("🧪 TEST: Threading is working!")

    test_t = threading.Thread(target=test_thread)
    test_t.start()
    test_t.join()


def start_udp_listener(ais_service):
    """Start the UDP listener in a background thread."""
    print("📦 MAIN: Creating UDP listener thread...")

    listener_thread = threading.Thread(
        target=ais_service.start_udp_listener,
        daemon=True
    )

    print("🚀 MAIN: Starting UDP listener thread...")
    listener_thread.start()

    # Give thread time to start
    time.sleep(2)

    # Verify thread is running
    if listener_thread.is_alive():
        print("✅ MAIN: UDP listener thread is running")
    else:
        print("❌ MAIN: UDP listener thread DIED!")
        raise RuntimeError("UDP listener failed to start")


def start_web_server(app):
    """Start the Flask web server."""
    print("🌐 MAIN: Starting Flask web server...")
    print(f"📡 MAIN: UDP listener active on port {app.config['AIS_DEV_PORT']}")

    # Start Flask (disable reloader to prevent double initialization)
    app.run(
        host="0.0.0.0",
        port=app.config.get('PORT', 5000),
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    main()