from models import db, Ship, Position
from datetime import datetime, timedelta

class AISDatabase:
    """Database service layer for AIS operations."""

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
                ship = Ship(mmsi=mmsi, first_seen=datetime.utcnow())
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
        """Save ship position data."""
        try:
            # Ensure ship exists
            ship = Ship.query.get(mmsi)
            if not ship:
                ship = Ship(mmsi=mmsi, first_seen=datetime.utcnow())
                db.session.add(ship)

            # Update ship's last seen
            ship.last_seen = datetime.utcnow()

            # Create position record
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
                timestamp=position_data['timestamp'] if isinstance(position_data['timestamp'], datetime) 
                         else datetime.fromisoformat(position_data['timestamp'].replace('Z', '+00:00')),
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
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

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
            result.append(ship_dict)

        return result

    @staticmethod
    def get_ship_details(mmsi):
        """Get detailed information for a specific ship."""
        ship = Ship.query.get(mmsi)
        return ship.to_dict() if ship else None

    @staticmethod
    def get_ship_track(mmsi, hours=24):
        """Get position history for a ship."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        positions = Position.query.filter(
            Position.mmsi == mmsi,
            Position.timestamp > cutoff_time
        ).order_by(Position.timestamp.asc()).all()

        return [pos.to_dict() for pos in positions]

    @staticmethod
    def cleanup_old_positions(days=7):
        """Remove position data older than specified days."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)

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

            # Active ships in last hour
            cutoff = datetime.utcnow() - timedelta(hours=1)
            active_ships = Ship.query.filter(Ship.last_seen > cutoff).count()

            return {
                'total_ships': ship_count,
                'total_positions': position_count,
                'active_ships_last_hour': active_ships
            }

        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}

class AISMessageProcessor:
    """Handles processing of decoded AIS messages."""

    def __init__(self, ships_dict, ship_details_dict, highlighted_mmsis):
        self.ships = ships_dict
        self.ship_details = ship_details_dict
        self.highlighted_mmsis = highlighted_mmsis

    def process_decoded_message(self, decoded_message, app_context):
        """Process a decoded AIS message and update both memory and database."""
        try:
            mmsi = str(decoded_message.mmsi)

            # Handle position messages (1, 2, 3, 18, 19, etc.)
            if hasattr(decoded_message, 'lat') and hasattr(decoded_message, 'lon'):
                self._process_position_message(decoded_message, mmsi, app_context)

            # Handle static data messages (5, 24)
            elif decoded_message.msg_type in [5, 24]:
                self._process_static_message(decoded_message, mmsi, app_context)

        except Exception as e:
            print(f"❌ Error processing decoded message: {e}")
            print(f"Message type: {getattr(decoded_message, 'msg_type', 'unknown')}")

    def _process_position_message(self, decoded_message, mmsi, app_context):
        """Process position-type AIS messages."""
        lat = decoded_message.lat
        lon = decoded_message.lon

        if lat is not None and lon is not None and lat != 91.0 and lon != 181.0:
            # Update in-memory data for real-time display
            self.ships[mmsi] = {
                "lat": float(lat),
                "lon": float(lon)
            }

            ship_info = {
                'mmsi': mmsi,
                'msg_type': decoded_message.msg_type,
                'latitude': float(lat),
                'longitude': float(lon),
                'timestamp': datetime.utcnow()
            }

            # Add optional fields if available
            optional_fields = [
                ('speed', 'speed'),
                ('course', 'course'),
                ('heading', 'heading'),
                ('status', 'nav_status'),
                ('turn', 'turn_rate'),
                ('accuracy', 'position_accuracy')
            ]

            for attr, key in optional_fields:
                if hasattr(decoded_message, attr):
                    value = getattr(decoded_message, attr)
                    if value is not None:
                        ship_info[key] = value

            self.ship_details[mmsi] = ship_info
            print(f"📍 Ship {mmsi}: {lat:.4f}, {lon:.4f} (msg {decoded_message.msg_type})")

            # Save position to database using ORM
            with app_context():
                AISDatabase.save_position(mmsi, ship_info)
        else:
            print(f"⚠️ Invalid coordinates for MMSI {mmsi}: {lat}, {lon}")

    def _process_static_message(self, decoded_message, mmsi, app_context):
        """Process static data AIS messages."""
        # Get existing info or create new
        ship_info = self.ship_details.get(mmsi, {
            'mmsi': mmsi,
            'msg_type': decoded_message.msg_type,
            'timestamp': datetime.utcnow()
        })

        # Add static data fields
        static_fields = [
            ('shipname', 'ship_name'),
            ('ship_type', 'ship_type'),
            ('callsign', 'callsign'),
            ('imo', 'imo'),
            ('destination', 'destination'),
            ('eta_month', 'eta_month'),
            ('eta_day', 'eta_day'),
            ('eta_hour', 'eta_hour'),
            ('eta_minute', 'eta_minute'),
            ('draught', 'draught'),
            ('to_bow', 'to_bow'),
            ('to_stern', 'to_stern'),
            ('to_port', 'to_port'),
            ('to_starboard', 'to_starboard')
        ]

        for attr, key in static_fields:
            if hasattr(decoded_message, attr):
                value = getattr(decoded_message, attr)
                if value is not None:
                    # Clean up string fields
                    if isinstance(value, str):
                        value = value.strip('@').strip()
                    if value:  # Only add non-empty values
                        ship_info[key] = value

        self.ship_details[mmsi] = ship_info
        ship_name = ship_info.get('ship_name', 'Unknown')
        print(f"📋 Static data for {mmsi}: {ship_name} (msg {decoded_message.msg_type})")

        # Save static data to database using ORM
        with app_context():
            AISDatabase.save_ship_static_data(mmsi, ship_info)

class MultipartMessageBuffer:
    """Handles buffering and reassembly of multipart AIS messages."""

    def __init__(self):
        self.buffer = {}

    def add_fragment(self, line, total_fragments, fragment_number, message_id, channel):
        """Add a fragment to the buffer and return complete message if ready."""
        # Create unique key for this multipart message
        buffer_key = f"{message_id}_{channel}" if message_id else f"no_id_{channel}_{total_fragments}"

        if buffer_key not in self.buffer:
            self.buffer[buffer_key] = {
                'fragments': {},
                'total': total_fragments,
                'timestamp': datetime.now()
            }

        # Store this fragment
        self.buffer[buffer_key]['fragments'][fragment_number] = line

        # Check if we have all fragments
        if len(self.buffer[buffer_key]['fragments']) == total_fragments:
            # We have all fragments - reassemble
            fragments = self.buffer[buffer_key]['fragments']

            # Sort fragments by fragment number and create list
            sorted_fragments = []
            for i in range(1, total_fragments + 1):
                if i in fragments:
                    sorted_fragments.append(fragments[i])
                else:
                    print(f"⚠️ Missing fragment {i} for message {buffer_key}")
                    return None

            # Clean up the buffer
            del self.buffer[buffer_key]

            print(f"✅ Assembled multipart message {buffer_key} ({total_fragments} parts)")
            return sorted_fragments
        else:
            fragments_received = len(self.buffer[buffer_key]['fragments'])
            print(f"🔄 Buffering fragment {fragment_number}/{total_fragments} for {buffer_key} (have {fragments_received}/{total_fragments})")
            return None

    def cleanup_old_fragments(self, max_age_seconds=60):
        """Clean up old incomplete multipart messages."""
        current_time = datetime.now()
        keys_to_remove = []

        for key, data in self.buffer.items():
            if (current_time - data['timestamp']).total_seconds() > max_age_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            fragments_count = len(self.buffer[key]['fragments'])
            total_expected = self.buffer[key]['total']
            print(f"🧹 Cleaning up incomplete message {key} ({fragments_count}/{total_expected} fragments)")
            del self.buffer[key]

    def get_stats(self):
        """Get buffer statistics."""
        return {
            'buffered_message_count': len(self.buffer),
            'buffered_messages': {k: f"{len(v['fragments'])}/{v['total']}" for k, v in self.buffer.items()}
        }

class NMEAParser:
    """Handles parsing of NMEA message format."""

    @staticmethod
    def parse_nmea_fields(line):
        """Parse NMEA line and extract fragment information."""
        parts = line.split(',')
        if len(parts) < 6:
            return None

        try:
            return {
                'total_fragments': int(parts[1]),
                'fragment_number': int(parts[2]),
                'message_id': parts[3] if parts[3] else None,
                'channel': parts[4]
            }
        except (ValueError, IndexError):
            print(f"⚠️ Invalid NMEA format: {line}")
            return None

    @staticmethod
    def is_ais_message(line):
        """Check if line is an AIS message."""
        line = line.strip()
        return line and line.startswith(("!AIVDM", "!AIVDO"))