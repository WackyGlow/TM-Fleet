"""
Advanced cleanup routes for SpyFleet application.
Handles age-based cleanup functionality and configuration management.
"""

from flask import jsonify, request
from database import AISDatabase


def register_cleanup_routes(app):
    """Register age-based cleanup API endpoints."""

    @app.route("/api/cleanup/age-stats")
    def get_age_cleanup_stats():
        """Get statistics about old data that can be cleaned up by age."""
        position_hours = float(request.args.get('position_hours', app.config.get('POSITION_MAX_AGE_HOURS', 2.0)))
        ship_hours = float(request.args.get('ship_hours', app.config.get('SHIP_MAX_AGE_HOURS', 24.0)))

        stats = AISDatabase.get_old_position_stats(position_hours, ship_hours)
        return jsonify(stats)

    @app.route("/api/cleanup/age-cleanup", methods=["POST"])
    def perform_age_cleanup():
        """Manually trigger age-based cleanup."""
        try:
            data = request.get_json() or {}
            underway_minutes = int(data.get('underway_minutes', 2))
            moored_hours = int(data.get('moored_hours', 2))

            result = AISDatabase.cleanup_old_positions_by_navigation(underway_minutes, moored_hours)

            if result.get('error'):
                return jsonify({
                    "success": False,
                    "message": f"Navigation-based cleanup failed: {result['error']}"
                }), 500
            else:
                underway_deleted = result.get('underway_positions_deleted', 0)
                moored_deleted = result.get('moored_positions_deleted', 0)

                return jsonify({
                    "success": True,
                    "message": f"Navigation-based cleanup completed: {underway_deleted} underway and {moored_deleted} moored positions deleted",
                    "result": result
                })

        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Navigation-based cleanup failed: {str(e)}"
            }), 500

    @app.route("/api/cleanup/status")
    def get_cleanup_status():
        """Get comprehensive cleanup status and configuration."""
        from services.ais_service import AISService
        ais_service = AISService.get_instance()

        if ais_service:
            # Use the existing get_stats method
            stats = ais_service.get_stats()

            # Get configuration values
            config_data = {
                "messages_processed": stats.get('message_count', 0),
                "ships_in_memory": stats.get('ships_count', 0),
                "ship_details_count": stats.get('details_count', 0),
                "cleanup_timer_active": stats.get('cleanup_timer_active', False),
                "multipart_buffer_stats": stats.get('buffer_stats', {}),

                # Configuration from app settings
                "underway_timeout_minutes": app.config.get('UNDERWAY_POSITION_TIMEOUT_MINUTES', 2),
                "moored_timeout_hours": app.config.get('MOORED_POSITION_TIMEOUT_HOURS', 2),
                "status_cleanup_enabled": app.config.get('ENABLE_STATUS_CLEANUP', True),
                "status_cleanup_interval_minutes": app.config.get('STATUS_CLEANUP_INTERVAL_MINUTES', 5),
                "message_cleanup_interval": app.config.get('CLEANUP_INTERVAL_MESSAGES', 1000),

                # Estimated values (since we don't track these specifically)
                "last_age_cleanup_at_message": 0  # This would require adding tracking to the service
            }

            return jsonify(config_data)
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