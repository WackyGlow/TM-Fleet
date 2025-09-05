from flask import jsonify
from database import AISDatabase


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