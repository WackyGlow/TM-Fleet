from models import db, Ship, TrackedShip, User
from datetime import datetime, UTC


class TrackingService:
    """Service class for ship tracking operations."""

    @staticmethod
    def get_tracked_ships(company_id=None, user_id=None):
        """Get tracked ships with optional filtering by company or user."""
        try:
            query = TrackedShip.query.join(Ship, TrackedShip.mmsi == Ship.mmsi)

            # Apply filters
            if company_id:
                query = query.filter(TrackedShip.company_id == company_id)

            if user_id:
                query = query.filter(TrackedShip.added_by_user_id == user_id)

            tracked_ships = query.all()
            result = []

            for tracked in tracked_ships:
                tracked_dict = tracked.to_dict()
                # Add latest position if available
                if tracked.ship:
                    latest_pos = tracked.ship.latest_position
                    if latest_pos:
                        tracked_dict['ship_data'].update({
                            'latitude': latest_pos.latitude,
                            'longitude': latest_pos.longitude,
                            'course': latest_pos.course,
                            'speed': latest_pos.speed,
                            'heading': latest_pos.heading,
                            'nav_status': latest_pos.nav_status,
                            'is_active': tracked.ship.is_active()
                        })
                result.append(tracked_dict)

            return result
        except Exception as e:
            print(f"❌ Error getting tracked ships: {e}")
            return []

    @staticmethod
    def get_company_tracked_ships(user_id):
        """Get all tracked ships for a company (for company admin users)."""
        try:
            user = User.query.get(user_id)
            if not user or user.role != 'company':
                return []

            return TrackingService.get_tracked_ships(company_id=user.company_id)

        except Exception as e:
            print(f"❌ Error getting company tracked ships: {e}")
            return []

    @staticmethod
    def get_user_assigned_ships(user_id):
        """Get ships assigned to a specific company user."""
        try:
            user = User.query.get(user_id)
            if not user:
                return []

            # For now, return empty list as assignment system isn't fully implemented
            # In the future, this would query the assignment table
            return []

        except Exception as e:
            print(f"❌ Error getting user assigned ships: {e}")
            return []

    @staticmethod
    def get_user_tracked_ships(user_id):
        """Get ships tracked by a specific user (free users)."""
        try:
            return TrackingService.get_tracked_ships(user_id=user_id)

        except Exception as e:
            print(f"❌ Error getting user tracked ships: {e}")
            return []

    @staticmethod
    def add_tracked_ship(mmsi, name=None, notes=None, added_by=None,
                         added_by_user_id=None, company_id=None):
        """Add a ship to the tracking list with proper company and user associations."""
        try:
            # Get user and company info
            if added_by_user_id:
                user = User.query.get(added_by_user_id)
                if not user:
                    return {'success': False, 'message': 'User not found'}

                # Use user's company if not specified
                if not company_id:
                    company_id = user.company_id

                # Check if user can track more ships
                can_track, message = user.can_track_ship()
                if not can_track:
                    return {'success': False, 'message': message}

            if not company_id:
                return {'success': False, 'message': 'Company ID is required'}

            # Check if already tracked by this company
            existing = TrackedShip.query.filter_by(mmsi=mmsi, company_id=company_id).first()
            if existing:
                return {'success': False, 'message': 'Ship is already being tracked by this company'}

            # Check company tracking limit
            from .company_service import CompanyService
            limit_check = CompanyService.check_company_tracking_limit(company_id)
            if not limit_check['can_track']:
                return {'success': False, 'message': limit_check['message']}

            # Ensure ship exists in database
            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.now(UTC))
                db.session.add(ship)

            # Create tracked ship entry
            tracked_ship = TrackedShip(
                mmsi=mmsi,
                name=name or (ship.ship_name if ship.ship_name else None),
                notes=notes,
                company_id=company_id,
                added_by_user_id=added_by_user_id,
                added_by=added_by,  # Legacy field
                added_date=datetime.now(UTC)
            )

            db.session.add(tracked_ship)
            db.session.commit()

            return {'success': True, 'message': 'Ship added to tracking list'}

        except Exception as e:
            print(f"❌ Error adding tracked ship {mmsi}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error adding ship: {str(e)}'}

    @staticmethod
    def remove_tracked_ship(mmsi, removed_by_user_id=None, company_id=None):
        """Remove a ship from the tracking list with proper user verification."""
        try:
            query = TrackedShip.query.filter_by(mmsi=mmsi)

            # If company_id specified, filter by company
            if company_id:
                query = query.filter_by(company_id=company_id)
            elif removed_by_user_id:
                # Get user's company
                user = User.query.get(removed_by_user_id)
                if user:
                    query = query.filter_by(company_id=user.company_id)

            tracked_ship = query.first()
            if not tracked_ship:
                return {'success': False, 'message': 'Ship is not being tracked'}

            # Check permissions
            if removed_by_user_id:
                user = User.query.get(removed_by_user_id)
                if user:
                    # Admin can remove any, company admin can remove company ships,
                    # users can only remove ships they added
                    if user.role == 'admin':
                        pass  # Admin can remove any
                    elif user.role == 'company' and tracked_ship.company_id == user.company_id:
                        pass  # Company admin can remove company ships
                    elif tracked_ship.added_by_user_id == user_id:
                        pass  # User can remove their own ships
                    else:
                        return {'success': False, 'message': 'You do not have permission to remove this ship'}

            db.session.delete(tracked_ship)
            db.session.commit()

            return {'success': True, 'message': 'Ship removed from tracking list'}

        except Exception as e:
            print(f"❌ Error removing tracked ship {mmsi}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error removing ship: {str(e)}'}

    @staticmethod
    def update_tracked_ship(mmsi, name=None, notes=None, updated_by_user_id=None, company_id=None):
        """Update tracked ship information with proper user verification."""
        try:
            query = TrackedShip.query.filter_by(mmsi=mmsi)

            # If company_id specified, filter by company
            if company_id:
                query = query.filter_by(company_id=company_id)
            elif updated_by_user_id:
                # Get user's company
                user = User.query.get(updated_by_user_id)
                if user:
                    query = query.filter_by(company_id=user.company_id)

            tracked_ship = query.first()
            if not tracked_ship:
                return {'success': False, 'message': 'Ship is not being tracked'}

            # Check permissions (same logic as remove)
            if updated_by_user_id:
                user = User.query.get(updated_by_user_id)
                if user:
                    if user.role == 'admin':
                        pass  # Admin can edit any
                    elif user.role == 'company' and tracked_ship.company_id == user.company_id:
                        pass  # Company admin can edit company ships
                    elif tracked_ship.added_by_user_id == updated_by_user_id:
                        pass  # User can edit their own ships
                    else:
                        return {'success': False, 'message': 'You do not have permission to edit this ship'}

            # Update the tracked ship
            if name is not None:
                tracked_ship.name = name
            if notes is not None:
                tracked_ship.notes = notes

            db.session.commit()

            return {'success': True, 'message': 'Tracked ship updated successfully'}

        except Exception as e:
            print(f"❌ Error updating tracked ship {mmsi}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error updating ship: {str(e)}'}

    @staticmethod
    def get_tracked_mmsis(company_id=None):
        """Get set of all tracked MMSIs for quick lookup, optionally filtered by company."""
        try:
            query = TrackedShip.query

            if company_id:
                query = query.filter_by(company_id=company_id)

            tracked_ships = query.all()
            return {ship.mmsi for ship in tracked_ships}
        except Exception as e:
            print(f"❌ Error getting tracked MMSIs: {e}")
            return set()

    @staticmethod
    def is_ship_tracked(mmsi, company_id=None):
        """Check if a ship is being tracked, optionally by a specific company."""
        try:
            query = TrackedShip.query.filter_by(mmsi=mmsi)

            if company_id:
                query = query.filter_by(company_id=company_id)

            return query.first() is not None

        except Exception as e:
            print(f"❌ Error checking if ship is tracked: {e}")
            return False

    @staticmethod
    def get_tracking_stats(company_id=None, user_id=None):
        """Get tracking statistics."""
        try:
            stats = {}

            if company_id:
                # Company-level stats
                total_tracked = TrackedShip.query.filter_by(company_id=company_id).count()

                # Active tracked ships (seen in last hour)
                from datetime import timedelta
                cutoff = datetime.now(UTC) - timedelta(hours=1)

                active_tracked = db.session.query(TrackedShip).join(Ship).filter(
                    TrackedShip.company_id == company_id,
                    Ship.last_seen > cutoff
                ).count()

                stats.update({
                    'total_tracked': total_tracked,
                    'active_tracked': active_tracked,
                    'inactive_tracked': total_tracked - active_tracked
                })

            if user_id:
                # User-level stats
                user_tracked = TrackedShip.query.filter_by(added_by_user_id=user_id).count()

                user = User.query.get(user_id)
                if user:
                    can_track, message = user.can_track_ship()
                    limit = user.get_tracking_limit()

                    stats.update({
                        'user_tracked': user_tracked,
                        'can_track_more': can_track,
                        'tracking_limit': limit,
                        'remaining': (limit - user_tracked) if limit else None
                    })

            return stats

        except Exception as e:
            print(f"❌ Error getting tracking stats: {e}")
            return {}