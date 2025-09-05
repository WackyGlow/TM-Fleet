# database/stats.py
from datetime import datetime, timedelta, UTC
from models import Ship, Position, TrackedShip, db


class StatsMixin:
    @staticmethod
    def get_database_stats():
        """Get database-wide statistics."""
        try:
            ship_count = Ship.query.count()
            position_count = Position.query.count()
            tracked_count = TrackedShip.query.count()

            # active ships in last hour
            cutoff = datetime.now(UTC) - timedelta(hours=1)
            active_ships = Ship.query.filter(Ship.last_seen > cutoff).count()

            return {
                'total_ships': ship_count,
                'total_positions': position_count,
                'tracked_ships': tracked_count,
                'active_ships_last_hour': active_ships
            }
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}

    @staticmethod
    def get_position_age_stats(underway_minutes=2, moored_hours=1):
        """Detailed position statistics grouped by nav status for the UI."""
        current_time = datetime.now(UTC)
        underway_cutoff = current_time - timedelta(minutes=underway_minutes)
        moored_cutoff = current_time - timedelta(hours=moored_hours)

        underway_q = Position.query.filter(~Position.nav_status.in_([1, 5, 6]))
        moored_q = Position.query.filter(Position.nav_status.in_([1, 5, 6]))
        unknown_q = Position.query.filter(Position.nav_status.is_(None))

        return {
            "underway_ships": db.session.query(Position.mmsi).filter(~Position.nav_status.in_([1, 5, 6])).distinct().count(),
            "underway_total_positions": underway_q.count(),
            "old_underway_positions": underway_q.filter(Position.timestamp < underway_cutoff).count(),
            "moored_ships": db.session.query(Position.mmsi).filter(Position.nav_status.in_([1, 5, 6])).distinct().count(),
            "moored_total_positions": moored_q.count(),
            "old_moored_positions": moored_q.filter(Position.timestamp < moored_cutoff).count(),
            "unknown_total_positions": unknown_q.count(),
            "unknown_old_positions": unknown_q.filter(Position.timestamp < moored_cutoff).count(),
        }