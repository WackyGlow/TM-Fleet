# database/ships.py
from datetime import datetime, timedelta, UTC
from models import db, Ship, Position, TrackedShip

class ShipMixin:
    # ---------- SEARCH & LIST ----------
    @staticmethod
    def search_ships(query, limit=20):
        """Search ships by name, MMSI, or callsign."""
        try:
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

    @staticmethod
    def get_all_ships_paginated(page=1, per_page=50, sort_field='ship_name',
                                sort_direction='asc', search_query=''):
        """List ships with pagination/sorting and optional search."""
        try:
            valid_fields = {
                'mmsi': Ship.mmsi,
                'ship_name': Ship.ship_name,
                'imo': Ship.imo,
                'ship_type': Ship.ship_type,
                'last_seen': Ship.last_seen,
                'first_seen': Ship.first_seen
            }
            sort_column = valid_fields.get(sort_field, Ship.ship_name)
            query = Ship.query

            if search_query:
                search_filter = db.or_(
                    Ship.mmsi.contains(search_query),
                    Ship.ship_name.contains(search_query),
                    Ship.callsign.contains(search_query),
                    Ship.imo.contains(search_query)
                )
                query = query.filter(search_filter)

            query = query.order_by(sort_column.asc()
                                   if sort_direction.lower() == 'asc'
                                   else sort_column.desc())
            total = query.count()
            ships = query.offset((page - 1) * per_page).limit(per_page).all()

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
                'ships': [], 'total': 0, 'page': page, 'per_page': per_page,
                'total_pages': 0, 'search_query': search_query
            }

    # ---------- SINGLE-SHIP READS / WRITES ----------
    @staticmethod
    def save_ship_static_data(mmsi, ship_data):
        """Save or update ship static data."""
        try:
            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.now(UTC))
                db.session.add(ship)
            ship.update_static_data(ship_data)
            db.session.commit()
            return True
        except Exception as e:
            print(f"❌ Error saving ship static data for {mmsi}: {e}")
            db.session.rollback()
            return False

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
        """Get position history for a ship (current position only)."""
        position = Position.query.filter_by(mmsi=mmsi).first()
        if position:
            return [position.to_dict()]
        return []

    @staticmethod
    def get_recent_ships():
        """Ships with fresh positions (timeout depends on nav status)."""
        current_time = datetime.now(UTC)
        underway_cutoff = current_time - timedelta(minutes=2)  # moving ships
        moored_cutoff = current_time - timedelta(hours=2)      # stationary ships

        ships_with_positions = db.session.query(Ship).join(Position).all()
        result = []
        for ship in ships_with_positions:
            latest_pos = ship.latest_position
            if not latest_pos:
                continue

            is_stationary = latest_pos.nav_status in [1, 5, 6]  # anchor, moored, aground
            cutoff_time = moored_cutoff if is_stationary else underway_cutoff

            if latest_pos.timestamp.replace(tzinfo=UTC) > cutoff_time:
                ship_dict = ship.to_dict()
                ship_dict.update({
                    'latitude': latest_pos.latitude,
                    'longitude': latest_pos.longitude,
                    'course': latest_pos.course,
                    'speed': latest_pos.speed,
                    'heading': latest_pos.heading,
                    'nav_status': latest_pos.nav_status
                })
                ship_dict['is_tracked'] = ship.is_tracked
                result.append(ship_dict)
        return result

    # ---------- TRACKED SHIPS ----------
    @staticmethod
    def get_tracked_ships():
        """Tracked ships with latest positional data merged in."""
        try:
            tracked_ships = TrackedShip.query.join(
                Ship, TrackedShip.mmsi == Ship.mmsi
            ).all()
            result = []
            for tracked in tracked_ships:
                tracked_dict = tracked.to_dict()
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
                result.append(tracked_dict)
            return result
        except Exception as e:
            print(f"❌ Error getting tracked ships: {e}")
            return []

    @staticmethod
    def add_tracked_ship(mmsi, name=None, notes=None, added_by=None):
        """Add a ship to the tracking list."""
        try:
            existing = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if existing:
                return {'success': False, 'message': 'Ship is already being tracked'}

            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.now(UTC))
                db.session.add(ship)

            tracked_ship = TrackedShip(
                mmsi=mmsi,
                name=name or (ship.ship_name if ship.ship_name else None),
                notes=notes,
                added_by=added_by,
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
    def remove_tracked_ship(mmsi):
        """Remove a ship from the tracking list."""
        try:
            tracked_ship = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if not tracked_ship:
                return {'success': False, 'message': 'Ship is not being tracked'}
            db.session.delete(tracked_ship)
            db.session.commit()
            return {'success': True, 'message': 'Ship removed from tracking list'}
        except Exception as e:
            print(f"❌ Error removing tracked ship {mmsi}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error removing ship: {str(e)}'}

    @staticmethod
    def update_tracked_ship(mmsi, name=None, notes=None):
        """Update tracked ship information."""
        try:
            tracked_ship = TrackedShip.query.filter_by(mmsi=mmsi).first()
            if not tracked_ship:
                return {'success': False, 'message': 'Ship is not being tracked'}
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
    def get_tracked_mmsis():
        """Get set of all tracked MMSIs for quick lookup."""
        try:
            tracked_ships = TrackedShip.query.all()
            return {ship.mmsi for ship in tracked_ships}
        except Exception as e:
            print(f"❌ Error getting tracked MMSIs: {e}")
            return set()
