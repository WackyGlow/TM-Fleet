"""
Flask routes for SpyFleet application.
Organized by functionality: views, API endpoints, and debug routes.
"""

from flask import render_template, jsonify, request
from database import AISDatabase


def register_routes(app):
    """Register all application routes."""
    register_view_routes(app)
    register_api_routes(app)
    register_debug_routes(app)


def register_view_routes(app):
    """Register HTML view routes."""

    @app.route("/")
    def index():
        """Main map view."""
        return render_template("map.html")

    @app.route("/track")
    def track_ships():
        """Track ships management page."""
        return render_template("trackships.html")

    @app.route("/info")
    def info():
        """Information page."""
        return render_template("info.html")


def register_api_routes(app):
    """Register API endpoints."""

    # Ship data endpoints
    @app.route("/ships")
    def get_ships():
        """Return ship data for the frontend (real-time memory data)."""
        from services.ais_service import AISService
        ais_service = AISService.get_instance()
        tracked_mmsis = AISDatabase.get_tracked_mmsis()

        return jsonify({
            "ships": ais_service.ships,
            "highlighted": list(tracked_mmsis),
            "details": ais_service.ship_details
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
        ship_track = AISDatabase.get_ship_track(mmsi, hours=2)

        return jsonify({
            "ship": ship_details_db,
            "track": ship_track
        })

    @app.route("/db/stats")
    def get_db_stats():
        """Get database statistics."""
        return jsonify(AISDatabase.get_database_stats())

    @app.route("/api/ships/all")
    def get_all_ships():
        """Get all ships with pagination, sorting, and optional search."""
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        sort_field = request.args.get('sort', 'ship_name')
        sort_direction = request.args.get('direction', 'asc')
        search_query = request.args.get('search', '').strip()

        # Limit per_page to prevent abuse
        per_page = min(per_page, 200)

        ships_data = AISDatabase.get_all_ships_paginated(
            page, per_page, sort_field, sort_direction, search_query
        )
        return jsonify(ships_data)

    @app.route("/api/ships/search")
    def search_ships():
        """Search ships by name, MMSI, or callsign."""
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))

        if not query:
            return jsonify({"ships": []})

        ships = AISDatabase.search_ships(query, limit)
        return jsonify({"ships": ships})

    # Tracked ships endpoints
    @app.route("/api/tracked-ships", methods=["GET"])
    def get_tracked_ships():
        """Get all tracked ships."""
        tracked_ships = AISDatabase.get_tracked_ships()
        return jsonify({"tracked_ships": tracked_ships})

    @app.route("/api/tracked-ships", methods=["POST"])
    def add_tracked_ship():
        """Add a ship to tracking list."""
        data = request.get_json()

        if not data or 'mmsi' not in data:
            return jsonify({"success": False, "message": "MMSI is required"}), 400

        mmsi = data['mmsi'].strip()
        name = data.get('name', '').strip() or None
        notes = data.get('notes', '').strip() or None
        added_by = data.get('added_by', 'User')

        result = AISDatabase.add_tracked_ship(mmsi, name, notes, added_by)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route("/api/tracked-ships/<mmsi>", methods=["DELETE"])
    def remove_tracked_ship(mmsi):
        """Remove a ship from tracking list."""
        result = AISDatabase.remove_tracked_ship(mmsi)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    @app.route("/api/tracked-ships/<mmsi>", methods=["PUT"])
    def update_tracked_ship(mmsi):
        """Update tracked ship information."""
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        name = data.get('name', '').strip() or None
        notes = data.get('notes', '').strip() or None

        result = AISDatabase.update_tracked_ship(mmsi, name, notes)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    @app.route("/api/ship/<mmsi>/toggle-tracking", methods=["POST"])
    def toggle_ship_tracking(mmsi):
        """Toggle tracking status for a ship."""
        data = request.get_json() or {}

        # Check if ship is currently tracked
        ship_details_db = AISDatabase.get_ship_details(mmsi)
        if not ship_details_db:
            return jsonify({"success": False, "message": "Ship not found"}), 404

        if ship_details_db.get('is_tracked', False):
            # Remove from tracking
            result = AISDatabase.remove_tracked_ship(mmsi)
        else:
            # Add to tracking
            name = data.get('name', '').strip() or None
            notes = data.get('notes', '').strip() or None
            added_by = data.get('added_by', 'User')
            result = AISDatabase.add_tracked_ship(mmsi, name, notes, added_by)

        return jsonify(result)


def register_debug_routes(app):
    """Register debug and maintenance endpoints."""

    @app.route("/debug")
    def debug():
        """Debug endpoint to see raw data."""
        from services.ais_service import AISService
        ais_service = AISService.get_instance()

        db_stats = AISDatabase.get_database_stats()
        buffer_stats = ais_service.multipart_buffer.get_stats() if ais_service else {}

        return jsonify({
            "ships_count": len(ais_service.ships) if ais_service else 0,
            "ships": ais_service.ships if ais_service else {},
            "details": ais_service.ship_details if ais_service else {},
            "multipart_buffer": buffer_stats,
            "database_stats": db_stats
        })

    @app.route("/db/cleanup")
    def cleanup_database():
        """Manual database cleanup endpoint."""
        deleted_count = AISDatabase.cleanup_old_positions(days=7)
        return jsonify({
            "message": "Database cleanup completed",
            "deleted_positions": deleted_count
        })