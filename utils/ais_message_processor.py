from datetime import datetime, UTC
from database import AISDatabase


class AISMessageProcessor:
    """Handles processing of decoded AIS messages."""

    def __init__(self, ships_dict, ship_details_dict, tracked_mmsis_callback):
        self.ships = ships_dict
        self.ship_details = ship_details_dict
        self.get_tracked_mmsis = tracked_mmsis_callback

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
                'timestamp': datetime.now(UTC)
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

            # Check if this is a tracked ship
            tracked_mmsis = self.get_tracked_mmsis()
            status_indicator = "🔴" if mmsi in tracked_mmsis else "📍"

            print(f"{status_indicator} Ship {mmsi}: {lat:.4f}, {lon:.4f} (msg {decoded_message.msg_type})")

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
            'timestamp': datetime.now(UTC)
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

        # Check if this is a tracked ship
        tracked_mmsis = self.get_tracked_mmsis()
        status_indicator = "🔴" if mmsi in tracked_mmsis else "📋"

        print(f"{status_indicator} Static data for {mmsi}: {ship_name} (msg {decoded_message.msg_type})")

        # Save static data to database using ORM
        with app_context():
            AISDatabase.save_ship_static_data(mmsi, ship_info)