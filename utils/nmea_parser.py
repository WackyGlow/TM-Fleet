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