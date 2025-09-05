# database/stats.py
from datetime import datetime, timedelta, UTC
from models import Ship, Position, TrackedShip

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
        """Detailed position statistics grouped by nav status."""
        current_time = datetime.now(UTC)
        underway_cutoff = current_time - timedelta(minutes=underway_minutes)
        moored_cutoff = current_time - timedelta(hours=moored_hours)

        underway_q = Position.query.filter(~Position.nav_status.in_([1, 5, 6]))
        moored_q = Position.query.filter(Position.nav_status.in_([1, 5, 6]))
        unknown_q = Position.query.filter(Position.nav_status.is_(None))

        # Counts
        underway_total = underway_q.count()
        moored_total = moored_q.count()
        unknown_total = unknown_q.count()

        underway_old = underway_q.filter(Position.timestamp < underway_cutoff).count()
        moored_old = moored_q.filter(Position.timestamp < moored_cutoff).count()
        unknown_old = unknown_q.filter(Position.timestamp < moored_cutoff).count()

        underway_ships = db.session.query(Position.mmsi).filter(~Position.nav_status.in_([1, 5, 6])).distinct().count()
        moored_ships = db.session.query(Position.mmsi).filter(Position.nav_status.in_([1, 5, 6])).distinct().count()

        return {
            "underway_ships": underway_ships,
            "underway_total_positions": underway_total,
            "old_underway_positions": underway_old,
            "moored_ships": moored_ships,
            "moored_total_positions": moored_total,
            "old_moored_positions": moored_old,
            "unknown_total_positions": unknown_total,
            "unknown_old_positions": unknown_old,
        }