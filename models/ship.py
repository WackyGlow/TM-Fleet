from datetime import datetime, timezone, timedelta
from . import db


class Ship(db.Model):
    """Ship static data model."""
    __tablename__ = 'ships'

    mmsi = db.Column(db.String(20), primary_key=True)
    ship_name = db.Column(db.String(100))
    callsign = db.Column(db.String(20))
    ship_type = db.Column(db.Integer)
    imo = db.Column(db.String(20))
    destination = db.Column(db.String(100))
    draught = db.Column(db.Float)
    to_bow = db.Column(db.Integer)
    to_stern = db.Column(db.Integer)
    to_port = db.Column(db.Integer)
    to_starboard = db.Column(db.Integer)
    first_seen = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships will be defined in the related model files
    # positions = db.relationship('Position', backref='ship', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Ship {self.mmsi}: {self.ship_name or "Unknown"}>'

    def to_dict(self):
        """Convert ship to dictionary."""
        return {
            'mmsi': self.mmsi,
            'ship_name': self.ship_name,
            'callsign': self.callsign,
            'ship_type': self.ship_type,
            'imo': self.imo,
            'destination': self.destination,
            'draught': self.draught,
            'to_bow': self.to_bow,
            'to_stern': self.to_stern,
            'to_port': self.to_port,
            'to_starboard': self.to_starboard,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

    def update_static_data(self, ship_data):
        """Update ship static data from AIS message."""
        for field, value in ship_data.items():
            if value is not None and hasattr(self, field):
                setattr(self, field, value)

        self.last_seen = datetime.now(timezone.utc)

    def is_active(self, hours=1):
        """Check if ship has been seen in the last N hours."""
        if not self.last_seen:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return self.last_seen > cutoff

    @property
    def is_tracked(self):
        """Check if this ship is being tracked."""
        # Import here to avoid circular imports
        from .tracked_ship import TrackedShip
        return TrackedShip.query.filter_by(mmsi=self.mmsi).first() is not None

    @property
    def latest_position(self):
        """Return the ship's most recent position if available."""
        from .position import Position
        """Return the ship's most recent position if available, using eager-loaded relationship."""
        # Assumes positions are ordered by timestamp descending due to relationship order_by
        return self.positions[0] if self.positions else None
