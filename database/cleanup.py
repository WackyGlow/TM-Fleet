from datetime import datetime, timedelta, UTC
from models import db, Ship, Position

class CleanupMixin:
    @staticmethod
    def cleanup_old_positions_by_navigation(underway_minutes=2, moored_hours=2):
        """
        Remove old position records based on navigation status.
        Ships themselves are NEVER deleted.
        """
        try:
            current_time = datetime.now(UTC)
            underway_cutoff = current_time - timedelta(minutes=underway_minutes)
            moored_cutoff = current_time - timedelta(hours=moored_hours)

            old_underway_positions = Position.query.filter(
                Position.timestamp < underway_cutoff,
                ~Position.nav_status.in_([1, 5, 6])  # not at anchor, moored, or aground
            ).count()

            old_moored_positions = Position.query.filter(
                Position.timestamp < moored_cutoff,
                Position.nav_status.in_([1, 5, 6])  # at anchor, moored, or aground
            ).count()

            if old_underway_positions == 0 and old_moored_positions == 0:
                print(f"🧹 No old positions to cleanup (underway >{underway_minutes}min, moored >{moored_hours}h)")
                return {
                    'underway_positions_deleted': 0,
                    'moored_positions_deleted': 0,
                    'underway_cutoff': underway_cutoff.isoformat(),
                    'moored_cutoff': moored_cutoff.isoformat()
                }

            print("🧹 Starting position cleanup by navigation status...")
            print(f"   - Underway positions older than {underway_minutes}min ({underway_cutoff}): {old_underway_positions}")
            print(f"   - Moored positions older than {moored_hours}h ({moored_cutoff}): {old_moored_positions}")

            underway_deleted = db.session.query(Position).filter(
                Position.timestamp < underway_cutoff,
                ~Position.nav_status.in_([1, 5, 6])
            ).delete(synchronize_session=False)

            moored_deleted = db.session.query(Position).filter(
                Position.timestamp < moored_cutoff,
                Position.nav_status.in_([1, 5, 6])
            ).delete(synchronize_session=False)

            db.session.commit()

            print("✅ Position cleanup completed:")
            print(f"   - Deleted {underway_deleted} old underway position records")
            print(f"   - Deleted {moored_deleted} old moored position records")

            return {
                'underway_positions_deleted': underway_deleted,
                'moored_positions_deleted': moored_deleted,
                'underway_cutoff': underway_cutoff.isoformat(),
                'moored_cutoff': moored_cutoff.isoformat()
            }

        except Exception as e:
            print(f"❌ Error in position cleanup: {e}")
            db.session.rollback()
            return {
                'underway_positions_deleted': 0,
                'moored_positions_deleted': 0,
                'error': str(e)
            }

    @staticmethod
    def cleanup_old_positions(days=7):
        """
        Remove duplicate position records, keeping only the most recent one per ship.
        Useful for one-time cleanup.
        """
        try:
            total_before = Position.query.count()
            ships_count = db.session.query(Position.mmsi).distinct().count()

            if total_before <= ships_count:
                print("🧹 No cleanup needed - already optimized")
                return 0

            print(f"🧹 Cleaning up {total_before - ships_count} duplicate position records...")

            subquery = db.session.query(
                Position.mmsi,
                db.func.max(Position.id).label('max_id')
            ).group_by(Position.mmsi).subquery()

            deleted_count = db.session.query(Position).filter(
                ~Position.id.in_(db.session.query(subquery.c.max_id))
            ).delete(synchronize_session=False)

            db.session.commit()

            print(f"🧹 Cleaned up {deleted_count} old position records")
            return deleted_count

        except Exception as e:
            print(f"❌ Error cleaning up positions: {e}")
            db.session.rollback()
            return 0

    @staticmethod
    def get_old_position_stats(underway_minutes=2, moored_hours=2):
        """
        Get statistics about old position records that would be cleaned up.
        Ships are never deleted.
        """
        try:
            current_time = datetime.now(UTC)
            underway_cutoff = current_time - timedelta(minutes=underway_minutes)
            moored_cutoff = current_time - timedelta(hours=moored_hours)

            old_underway_positions = Position.query.filter(
                Position.timestamp < underway_cutoff,
                ~Position.nav_status.in_([1, 5, 6])
            ).count()

            old_moored_positions = Position.query.filter(
                Position.timestamp < moored_cutoff,
                Position.nav_status.in_([1, 5, 6])
            ).count()

            total_positions = Position.query.count()
            total_ships = Ship.query.count()

            return {
                'old_underway_positions': old_underway_positions,
                'old_moored_positions': old_moored_positions,
                'total_old_positions': old_underway_positions + old_moored_positions,
                'total_positions': total_positions,
                'total_ships': total_ships,
                'underway_cutoff': underway_cutoff.isoformat(),
                'moored_cutoff': moored_cutoff.isoformat(),
                'underway_minutes': underway_minutes,
                'moored_hours': moored_hours,
                'cleanup_needed': old_underway_positions > 0 or old_moored_positions > 0,
            }

        except Exception as e:
            print(f"❌ Error getting old position stats: {e}")
            return {
                'old_underway_positions': 0,
                'old_moored_positions': 0,
                'total_old_positions': 0,
                'total_positions': 0,
                'total_ships': 0,
                'error': str(e)
            }

    @staticmethod
    def get_cleanup_stats():
        """Get statistics about duplicate position records that could be cleaned up."""
        try:
            total_positions = Position.query.count()
            unique_ships = db.session.query(Position.mmsi).distinct().count()
            duplicate_positions = total_positions - unique_ships

            return {
                'total_positions': total_positions,
                'unique_ships': unique_ships,
                'duplicate_positions': duplicate_positions,
                'cleanup_needed': duplicate_positions > 0
            }
        except Exception as e:
            print(f"❌ Error getting cleanup stats: {e}")
            return {}
