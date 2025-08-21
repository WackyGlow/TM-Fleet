from models import db, Ship, Position, TrackedShip, User
from datetime import datetime, timedelta, UTC


class AISDatabase:
    """Database service layer for AIS operations with authentication support."""

    @staticmethod
    def get_all_ships_paginated(page=1, per_page=50, sort_field='ship_name', sort_direction='asc', search_query=''):
        """Get all ships with pagination, sorting, and optional search."""
        try:
            # Define valid sort fields
            valid_fields = {
                'mmsi': Ship.mmsi,
                'ship_name': Ship.ship_name,
                'imo': Ship.imo,
                'ship_type': Ship.ship_type,
                'last_seen': Ship.last_seen,
                'first_seen': Ship.first_seen
            }

            # Default to ship_name if invalid field
            sort_column = valid_fields.get(sort_field, Ship.ship_name)

            # Build query
            query = Ship.query

            # Apply search filter if provided
            if search_query:
                search_filter = db.or_(
                    Ship.mmsi.contains(search_query),
                    Ship.ship_name.contains(search_query),
                    Ship.callsign.contains(search_query),
                    Ship.imo.contains(search_query)
                )
                query = query.filter(search_filter)

            # Apply sorting
            if sort_direction.lower() == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Get total count
            total = query.count()

            # Apply pagination
            ships = query.offset((page - 1) * per_page).limit(per_page).all()

            result = []
            for ship in ships:
                ship_dict = ship.to_dict()
                # Add latest position if available
                latest_pos = ship.latest_position
                if latest_pos:
                    ship_dict.update({
                        'latitude': latest_pos.latitude,
                        'longitude': latest_pos.longitude,
                        'course': latest_pos.course,
                        'speed': latest_pos.speed,
                        'heading': latest_pos.heading,
                        'nav_status': latest_pos.nav_status
                    })
                # Add tracking status
                ship_dict['is_tracked'] = ship.is_tracked
                result.append(ship_dict)

            return {
                'ships': result,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page,
                'search_query': search_query
            }

        except Exception as e:
            print(f"❌ Error getting paginated ships: {e}")
            return {
                'ships': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'search_query': search_query
            }

    @staticmethod
    def init_database(app):
        """Initialize database with Flask app context."""
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")

    @staticmethod
    def save_ship_static_data(mmsi, ship_data):
        """Save or update ship static data."""
        try:
            # Get or create ship
            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.now(UTC))
                db.session.add(ship)

            # Update ship data
            ship.update_static_data(ship_data)

            db.session.commit()
            return True

        except Exception as e:
            print(f"❌ Error saving ship static data for {mmsi}: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def save_position(mmsi, position_data):
        """Save or update ship position data."""
        try:
            # Ensure ship exists
            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.now(UTC))
                db.session.add(ship)

            # Update ship's last seen
            ship.last_seen = datetime.now(UTC)

            # Parse timestamp
            timestamp = (
                position_data['timestamp']
                if isinstance(position_data['timestamp'], datetime)
                else datetime.fromisoformat(position_data['timestamp'].replace('Z', '+00:00'))
            )

            # Update existing position or create new
            position = Position.query.filter_by(mmsi=mmsi).first()
            if position:
                position.latitude = position_data['latitude']
                position.longitude = position_data['longitude']
                position.course = position_data.get('course')
                position.speed = position_data.get('speed')
                position.heading = position_data.get('heading')
                position.nav_status = position_data.get('nav_status')
                position.turn_rate = position_data.get('turn_rate')
                position.position_accuracy = position_data.get('position_accuracy')
                position.timestamp = timestamp
                position.message_type = position_data['msg_type']
            else:
                position = Position(
                    mmsi=mmsi,
                    latitude=position_data['latitude'],
                    longitude=position_data['longitude'],
                    course=position_data.get('course'),
                    speed=position_data.get('speed'),
                    heading=position_data.get('heading'),
                    nav_status=position_data.get('nav_status'),
                    turn_rate=position_data.get('turn_rate'),
                    position_accuracy=position_data.get('position_accuracy'),
                    timestamp=timestamp,
                    message_type=position_data['msg_type']
                )
                db.session.add(position)

            db.session.commit()
            return True

        except Exception as e:
            print(f"❌ Error saving position for {mmsi}: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def get_recent_ships(hours=24):
        """Get ships seen in the last N hours with their latest positions."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

        # Get ships with their latest position
        ships = db.session.query(Ship).filter(
            Ship.last_seen > cutoff_time
        ).order_by(Ship.last_seen.desc()).all()

        result = []
        for ship in ships:
            ship_dict = ship.to_dict()
            latest_pos = ship.latest_position
            if latest_pos:
                ship_dict.update({
                    'latitude': latest_pos.latitude,
                    'longitude': latest_pos.longitude,
                    'course': latest_pos.course,
                    'speed': latest_pos.speed,
                    'heading': latest_pos.heading,
                    'nav_status': latest_pos.nav_status
                })
            # Add tracking status
            ship_dict['is_tracked'] = ship.is_tracked
            result.append(ship_dict)

        return result

    @staticmethod
    def get_ship_details(mmsi):
        """Get detailed information for a specific ship."""
        ship = Ship.query.get(mmsi)
        if ship:
            ship_dict = ship.to_dict()
            ship_dict['is_tracked'] = ship.is_tracked
            return ship_dict
        return None

    @staticmethod
    def get_ship_track(mmsi, hours=24):
        """Get position history for a ship."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

        positions = Position.query.filter(
            Position.mmsi == mmsi,
            Position.timestamp > cutoff_time
        ).order_by(Position.timestamp.asc()).all()

        return [pos.to_dict() for pos in positions]

    @staticmethod
    def cleanup_old_positions(days=7):
        """Remove position data older than specified days."""
        try:
            cutoff_time = datetime.now(UTC) - timedelta(days=days)

            deleted_count = Position.query.filter(
                Position.timestamp < cutoff_time
            ).delete()

            db.session.commit()
            print(f"🧹 Cleaned up {deleted_count} old position records")
            return deleted_count

        except Exception as e:
            print(f"❌ Error cleaning up old positions: {e}")
            db.session.rollback()
            return 0

    @staticmethod
    def get_database_stats():
        """Get database statistics."""
        try:
            ship_count = Ship.query.count()
            position_count = Position.query.count()
            tracked_count = TrackedShip.query.count()

            # Active ships in last hour
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

    # Tracked ships management
    @staticmethod
    def get_tracked_ships():
        """Get all tracked ships with their current data."""
        try:
            tracked_ships = TrackedShip.query.join(Ship, TrackedShip.mmsi == Ship.mmsi).all()
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
                            'nav_status': latest_pos.nav_status
                        })
                    tracked_dict['is_active'] = tracked.ship.is_active()
                else:
                    tracked_dict['is_active'] = False
                result.append(tracked_dict)

            return result
        except Exception as e:
            print(f"❌ Error getting tracked ships: {e}")
            return []

    @staticmethod
    def add_tracked_ship(mmsi, name=None, notes=None, added_by=None, added_by_user_id=None):
        """Add a ship to the tracking list with user and audit logging."""
        try:
            # Check if already tracked
            existing = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if existing:
                return {'success': False, 'message': 'Ship is already being tracked'}

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
                added_by=added_by,
                added_date=datetime.now(UTC),
                added_by_user_id=added_by_user_id
            )

            db.session.add(tracked_ship)
            db.session.commit()

            return {'success': True, 'message': 'Ship added to tracking list'}

        except Exception as e:
            print(f"❌ Error adding tracked ship {mmsi}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error adding ship: {str(e)}'}

    @staticmethod
    def remove_tracked_ship(mmsi, removed_by_user_id=None):
        """Remove a ship from the tracking list with user and audit logging."""
        try:
            tracked_ship = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if not tracked_ship:
                return {'success': False, 'message': 'Ship is not being tracked'}

            ship_name = tracked_ship.name or 'Unknown'
            db.session.delete(tracked_ship)
            db.session.commit()

            return {'success': True, 'message': 'Ship removed from tracking list'}

        except Exception as e:
            print(f"❌ Error removing tracked ship {mmsi}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error removing ship: {str(e)}'}

    @staticmethod
    def update_tracked_ship(mmsi, name=None, notes=None, updated_by_user_id=None):
        """Update tracked ship information with user and audit logging."""
        try:
            tracked_ship = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if not tracked_ship:
                return {'success': False, 'message': 'Ship is not being tracked'}

            old_name = tracked_ship.name
            old_notes = tracked_ship.notes

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
    def get_user_tracked_ships(user_id):
        """Get tracked ships added by a specific user."""
        try:
            tracked = TrackedShip.query.filter_by(added_by_user_id=user_id).join(Ship).all()
            result = []
            for t in tracked:
                t_dict = t.to_dict()
                if t.ship:
                    latest_pos = t.ship.latest_position
                    if latest_pos:
                        t_dict['ship_data'].update({
                            'latitude': latest_pos.latitude,
                            'longitude': latest_pos.longitude,
                            'course': latest_pos.course,
                            'speed': latest_pos.speed,
                            'heading': latest_pos.heading,
                            'nav_status': latest_pos.nav_status
                        })
                    t_dict['is_active'] = t.ship.is_active()
                else:
                    t_dict['is_active'] = False
                result.append(t_dict)
            return result
        except Exception as e:
            print(f"❌ Error getting user tracked ships: {e}")
            return []

    @staticmethod
    def get_company_tracked_ships(company_id):
        """Get tracked ships for a company and its users."""
        try:
            company = User.query.get(company_id)
            if not company:
                return []

            company_users = getattr(company, 'company_users', [])
    def get_user_and_subordinates_tracked_ships(user_id):
        """Get tracked ships for a user and their subordinate users."""
        try:
            user = User.query.get(user_id)
            if not user:
                return []

            company_users = getattr(user, 'company_users', [])
            user_ids = [user.id] + [u.id for u in company_users]
            tracked = TrackedShip.query.filter(TrackedShip.added_by_user_id.in_(user_ids)).join(Ship).all()
            result = []
            for t in tracked:
                t_dict = t.to_dict()
                if t.ship:
                    latest_pos = t.ship.latest_position
                    if latest_pos:
                        t_dict['ship_data'].update({
                            'latitude': latest_pos.latitude,
                            'longitude': latest_pos.longitude,
                            'course': latest_pos.course,
                            'speed': latest_pos.speed,
                            'heading': latest_pos.heading,
                            'nav_status': latest_pos.nav_status
                        })
                    t_dict['is_active'] = t.ship.is_active()
                else:
                    t_dict['is_active'] = False
                result.append(t_dict)
            return result
        except Exception as e:
            print(f"❌ Error getting company tracked ships: {e}")
            return []

    @staticmethod
    def get_company_user_count(company_id):
        """Get number of users belonging to a company."""
        try:
            return User.query.filter_by(company_id=company_id).count()
        except Exception as e:
            print(f"❌ Error getting company user count: {e}")
            return 0

    @staticmethod
    def get_user_assigned_ships(user_id):
        """Get ships assigned to a company user."""
        try:
            user = User.query.get(user_id)
            if not user:
                return []

            if user.company_id:
                return AISDatabase.get_company_tracked_ships(user.company_id)
            return AISDatabase.get_user_tracked_ships(user_id)
        except Exception as e:
            print(f"❌ Error getting user assigned ships: {e}")
            return []

    @staticmethod
    def get_tracked_mmsis():
        """Get set of all tracked MMSIs for quick lookup."""
        try:
            tracked_ships = TrackedShip.query.all()
            return {ship.mmsi for ship in tracked_ships}
        except Exception as e:
            print(f"❌ Error getting tracked MMSIs: {e}")
            return set()

    @staticmethod
    def search_ships(query, limit=20):
        """Search ships by name, MMSI, or callsign."""
        try:
            # Search by MMSI, ship name, or callsign
            ships = Ship.query.filter(
                db.or_(
                    Ship.mmsi.contains(query),
                    Ship.ship_name.contains(query),
                    Ship.callsign.contains(query)
                )
            ).limit(limit).all()

            result = []
            for ship in ships:
                ship_dict = ship.to_dict()
                ship_dict['is_tracked'] = ship.is_tracked
                # Add latest position if available
                latest_pos = ship.latest_position
                if latest_pos:
                    ship_dict.update({
                        'latitude': latest_pos.latitude,
                        'longitude': latest_pos.longitude,
                        'last_seen': ship.last_seen.isoformat() if ship.last_seen else None
                    })
                result.append(ship_dict)

            return result
        except Exception as e:
            print(f"❌ Error searching ships: {e}")
            return []