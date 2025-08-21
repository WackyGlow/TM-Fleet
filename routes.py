"""
Flask routes for SpyFleet application.
Updated to add authentication protection to existing routes.
"""

from flask import render_template, jsonify, request, session, redirect, url_for
from auth import login_required  # ADD THIS IMPORT
from database import AISDatabase


def register_routes(app):
    """Register all application routes."""
    register_view_routes(app)
    register_api_routes(app)
    register_debug_routes(app)


def register_view_routes(app):
    """Register HTML view routes - ADD @login_required to existing routes."""

    @app.route("/")
    def index():
        """Root route - redirect to login if not authenticated, otherwise to map."""
        if 'user_id' in session:
            return redirect(url_for('map_view'))
        return redirect(url_for('auth.login'))

    @app.route("/map")  # CHANGED from "/" to "/map" since "/" now redirects to login
    @login_required     # ADD THIS
    def map_view():     # RENAMED from index() to map_view()
        """Main map view."""
        return render_template("map.html")

    @app.route("/track")
    @login_required     # ADD THIS
    def track_ships():
        """Track ships management page."""
        return render_template("trackships.html")

    @app.route("/info")
    @login_required     # ADD THIS
    def info():
        """Information page."""
        return render_template("info.html")


def register_api_routes(app):
    """Register API endpoints - ADD @login_required to existing API routes."""

    # Ship data endpoints
    @app.route("/ships")
    @login_required     # ADD THIS
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
    @login_required     # ADD THIS
    def get_db_ships():
        """Get recent ships from database."""
        recent_ships = AISDatabase.get_recent_ships(hours=24)
        return jsonify({"ships": recent_ships})

    @app.route("/db/ship/<mmsi>")
    @login_required     # ADD THIS
    def get_ship_info(mmsi):
        """Get detailed information for a specific ship."""
        ship_details_db = AISDatabase.get_ship_details(mmsi)
        ship_track = AISDatabase.get_ship_track(mmsi, hours=2)

        return jsonify({
            "ship": ship_details_db,
            "track": ship_track
        })

    @app.route("/db/stats")
    @login_required     # ADD THIS
    def get_db_stats():
        """Get database statistics."""
        return jsonify(AISDatabase.get_database_stats())

    @app.route("/api/ships/all")
    @login_required     # ADD THIS
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
    @login_required     # ADD THIS
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
    @login_required     # ADD THIS
    def get_tracked_ships():
        """Get all tracked ships."""
        tracked_ships = AISDatabase.get_tracked_ships()
        return jsonify({"tracked_ships": tracked_ships})

    @app.route("/api/tracked-ships", methods=["POST"])
    @login_required     # ADD THIS
    def add_tracked_ship():
        """Add a ship to tracking list - with role-based limits."""
        data = request.get_json()

        if not data or 'mmsi' not in data:
            return jsonify({"success": False, "message": "MMSI is required"}), 400

        # Get current user info
        user_id = session.get('user_id')
        username = session.get('username', 'User')

        # Check if user can track more ships
        from models import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 400

        can_track, message = user.can_track_ship()
        if not can_track:
            return jsonify({"success": False, "message": message}), 403

        mmsi = data['mmsi'].strip()
        name = data.get('name', '').strip() or None
        notes = data.get('notes', '').strip() or None

        result = AISDatabase.add_tracked_ship(
            mmsi=mmsi,
            name=name,
            notes=notes,
            added_by=username,
            added_by_user_id=user_id
        )

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route("/api/tracked-ships/<mmsi>", methods=["DELETE"])
    @login_required     # ADD THIS
    def remove_tracked_ship(mmsi):
        """Remove a ship from tracking list - with user verification."""
        user_id = session.get('user_id')
        user_role = session.get('user_role')

        # Admin can remove any tracked ship
        # Others can only remove ships they added
        if user_role != 'admin':
            from models import TrackedShip
            tracked_ship = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if tracked_ship and tracked_ship.added_by_user_id != user_id:
                return jsonify({"success": False, "message": "You can only remove ships you added"}), 403

        result = AISDatabase.remove_tracked_ship(mmsi, removed_by_user_id=user_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    @app.route("/api/tracked-ships/<mmsi>", methods=["PUT"])
    @login_required     # ADD THIS
    def update_tracked_ship(mmsi):
        """Update tracked ship information - with user verification."""
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        user_id = session.get('user_id')
        user_role = session.get('user_role')

        # Admin can update any tracked ship
        # Others can only update ships they added
        if user_role != 'admin':
            from models import TrackedShip
            tracked_ship = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if tracked_ship and tracked_ship.added_by_user_id != user_id:
                return jsonify({"success": False, "message": "You can only edit ships you added"}), 403

        name = data.get('name', '').strip() or None
        notes = data.get('notes', '').strip() or None

        result = AISDatabase.update_tracked_ship(
            mmsi=mmsi,
            name=name,
            notes=notes,
            updated_by_user_id=user_id
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    @app.route("/api/ship/<mmsi>/toggle-tracking", methods=["POST"])
    @login_required     # ADD THIS
    def toggle_ship_tracking(mmsi):
        """Toggle tracking status for a ship - with role-based limits."""
        data = request.get_json() or {}
        user_id = session.get('user_id')
        username = session.get('username', 'User')

        # Check if ship is currently tracked by this user
        from models import TrackedShip
        existing_track = TrackedShip.query.filter_by(mmsi=mmsi, added_by_user_id=user_id).first()

        if existing_track:
            # Remove from tracking
            result = AISDatabase.remove_tracked_ship(mmsi, removed_by_user_id=user_id)
        else:
            # Check if user can track more ships
            from models import User
            user = User.query.get(user_id)
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 400

            can_track, message = user.can_track_ship()
            if not can_track:
                return jsonify({"success": False, "message": message}), 403

            # Add to tracking
            name = data.get('name', '').strip() or None
            notes = data.get('notes', '').strip() or None
            result = AISDatabase.add_tracked_ship(
                mmsi=mmsi,
                name=name,
                notes=notes,
                added_by=username,
                added_by_user_id=user_id
            )

        return jsonify(result)

    @app.route("/api/user/tracking-status")
    @login_required
    def get_user_tracking_status():
        """Get current user's tracking status and limits."""
        user_id = session.get('user_id')

        from models import User, TrackedShip
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 400

        current_count = TrackedShip.query.filter_by(added_by_user_id=user_id).count()
        can_track, message = user.can_track_ship()
        limit = user.get_tracking_limit()

        return jsonify({
            "success": True,
            "current_count": current_count,
            "limit": limit,
            "remaining": None if limit is None else max(0, limit - current_count),
            "can_track": can_track,
            "message": message,
            "role": user.role
        })


def register_debug_routes(app):
    """Register debug and maintenance endpoints - ADD @login_required."""

    @app.route("/debug")
    @login_required     # ADD THIS
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
    @login_required     # ADD THIS
    def cleanup_database():
        """Manual database cleanup endpoint."""
        deleted_count = AISDatabase.cleanup_old_positions(days=7)
        return jsonify({
            "message": "Database cleanup completed",
            "deleted_positions": deleted_count
        })