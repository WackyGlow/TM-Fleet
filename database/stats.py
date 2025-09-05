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
