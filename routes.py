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
    register_cleanup_routes(app)  # NEW: Age-based cleanup routes


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

    @app.route("/admin/cleanup-stats")
    def cleanup_stats():
        """Get cleanup statistics."""
        stats = AISDatabase.get_cleanup_stats()
        return jsonify(stats)

    @app.route("/admin/cleanup-positions", methods=["POST"])
    def cleanup_positions():
        """Clean up old position records."""
        try:
            deleted_count = AISDatabase.cleanup_old_positions()
            return jsonify({
                "success": True,
                "message": f"Successfully cleaned up {deleted_count:,} old position records",
                "deleted_count": deleted_count
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Cleanup failed: {str(e)}"
            }), 500

def register_cleanup_routes(app):
    """Register NEW age-based cleanup API endpoints."""

    @app.route("/api/cleanup/age-stats")
    def get_age_cleanup_stats():
        """Get statistics about old data that can be cleaned up by age."""
        position_hours = float(request.args.get('position_hours', app.config.get('POSITION_MAX_AGE_HOURS', 2.0)))
        ship_hours = float(request.args.get('ship_hours', app.config.get('SHIP_MAX_AGE_HOURS', 24.0)))

        stats = AISDatabase.get_old_data_stats(position_hours, ship_hours)
        return jsonify(stats)

    @app.route("/api/cleanup/age-cleanup", methods=["POST"])
    def perform_age_cleanup():
        """Manually trigger age-based cleanup."""
        try:
            data = request.get_json() or {}
            position_hours = float(data.get('position_hours', app.config.get('POSITION_MAX_AGE_HOURS', 2.0)))
            ship_hours = float(data.get('ship_hours', app.config.get('SHIP_MAX_AGE_HOURS', 24.0)))

            result = AISDatabase.cleanup_old_data_by_age(position_hours, ship_hours)

            if result.get('error'):
                return jsonify({
                    "success": False,
                    "message": f"Age-based cleanup failed: {result['error']}"
                }), 500
            else:
                positions_deleted = result.get('positions_deleted', 0)
                ships_deleted = result.get('ships_deleted', 0)

                return jsonify({
                    "success": True,
                    "message": f"Age-based cleanup completed: {positions_deleted} positions and {ships_deleted} ships deleted",
                    "result": result
                })

        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Age-based cleanup failed: {str(e)}"
            }), 500

    @app.route("/api/cleanup/status")
    def get_cleanup_status():
        """Get comprehensive cleanup status and configuration."""
        from services.ais_service import AISService
        ais_service = AISService.get_instance()

        if ais_service:
            status = ais_service.get_cleanup_status()
            return jsonify(status)
        else:
            return jsonify({
                "error": "AIS service not available"
            }), 503

    @app.route("/api/cleanup/config")
    def get_cleanup_config():
        """Get current cleanup configuration."""
        return jsonify({
            "auto_cleanup_enabled": app.config.get('AUTO_CLEANUP_ENABLED', True),
            "position_max_age_hours": app.config.get('POSITION_MAX_AGE_HOURS', 2.0),
            "ship_max_age_hours": app.config.get('SHIP_MAX_AGE_HOURS', 24.0),
            "age_cleanup_interval": app.config.get('AGE_CLEANUP_INTERVAL', 1000),
            "duplicate_cleanup_interval": app.config.get('DUPLICATE_CLEANUP_INTERVAL', 5000),
            "auto_cleanup_interval_messages": app.config.get('AUTO_CLEANUP_INTERVAL_MESSAGES', 500)
        })

    @app.route("/api/cleanup/config", methods=["POST"])
    def update_cleanup_config():
        """Update cleanup configuration (runtime only)."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "message": "No configuration data provided"}), 400

            # Note: This only updates runtime config, not persistent config
            updated_settings = []

            if 'position_max_age_hours' in data:
                app.config['POSITION_MAX_AGE_HOURS'] = float(data['position_max_age_hours'])
                updated_settings.append(f"position_max_age_hours = {data['position_max_age_hours']}")

            if 'ship_max_age_hours' in data:
                app.config['SHIP_MAX_AGE_HOURS'] = float(data['ship_max_age_hours'])
                updated_settings.append(f"ship_max_age_hours = {data['ship_max_age_hours']}")

            if 'auto_cleanup_enabled' in data:
                app.config['AUTO_CLEANUP_ENABLED'] = bool(data['auto_cleanup_enabled'])
                updated_settings.append(f"auto_cleanup_enabled = {data['auto_cleanup_enabled']}")

            return jsonify({
                "success": True,
                "message": f"Configuration updated: {', '.join(updated_settings)}",
                "note": "Changes are runtime only and will reset on application restart"
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Configuration update failed: {str(e)}"
            }), 500