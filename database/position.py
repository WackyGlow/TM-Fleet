from datetime import datetime, UTC
from models import db, Ship, Position

class PositionMixin:
    @staticmethod
    def save_position(mmsi, position_data):
        """
        Save or update ship position data.
        Updates existing position record instead of creating new ones.
        """
        try:
            # Ensure the ship exists
            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.now(UTC))
                db.session.add(ship)

            # Update ship's last seen timestamp
            ship.last_seen = datetime.now(UTC)

            # Look for an existing position record for this ship
            existing_position = Position.query.filter_by(mmsi=mmsi).first()

            ts = position_data['timestamp']
            if not isinstance(ts, datetime):
                ts = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))

            if existing_position:
                # Update the existing record
                existing_position.latitude = position_data['latitude']
                existing_position.longitude = position_data['longitude']
                existing_position.course = position_data.get('course')
                existing_position.speed = position_data.get('speed')
                existing_position.heading = position_data.get('heading')
                existing_position.nav_status = position_data.get('nav_status')
                existing_position.turn_rate = position_data.get('turn_rate')
                existing_position.position_accuracy = position_data.get('position_accuracy')
                existing_position.timestamp = ts
                existing_position.message_type = position_data['msg_type']
            else:
                # Insert a new record (first time we see this ship)
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
                    timestamp=ts,
                    message_type=position_data['msg_type']
                )
                db.session.add(position)

            db.session.commit()
            return True

        except Exception as e:
            print(f"❌ Error saving position for {mmsi}: {e}")
            db.session.rollback()
            return False
