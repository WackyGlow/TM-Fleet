from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from sqlalchemy import Index

db = SQLAlchemy()


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

    # Relationship to positions
    positions = db.relationship('Position', backref='ship', lazy='dynamic', cascade='all, delete-orphan')

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

    @property
    def latest_position(self):
        """Get the most recent position for this ship."""
        return self.positions.order_by(Position.timestamp.desc()).first()

    def is_active(self, hours=1):
        """Check if ship has been seen in the last N hours."""
        if not self.last_seen:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return self.last_seen > cutoff

    @property
    def is_tracked(self):
        """Check if this ship is being tracked."""
        return TrackedShip.query.filter_by(mmsi=self.mmsi).first() is not None


class Position(db.Model):
    """Ship position data model."""
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    mmsi = db.Column(db.String(20), db.ForeignKey('ships.mmsi'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    course = db.Column(db.Float)
    speed = db.Column(db.Float)
    heading = db.Column(db.Integer)
    nav_status = db.Column(db.Integer)
    turn_rate = db.Column(db.Float)
    position_accuracy = db.Column(db.Boolean)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    message_type = db.Column(db.Integer)

    # Indexes for better performance
    __table_args__ = (
        Index('idx_positions_mmsi_timestamp', 'mmsi', 'timestamp'),
        Index('idx_positions_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f'<Position {self.mmsi}: {self.latitude}, {self.longitude} at {self.timestamp}>'

    def to_dict(self):
        """Convert position to dictionary."""
        return {
            'id': self.id,
            'mmsi': self.mmsi,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'course': self.course,
            'speed': self.speed,
            'heading': self.heading,
            'nav_status': self.nav_status,
            'turn_rate': self.turn_rate,
            'position_accuracy': self.position_accuracy,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'message_type': self.message_type
        }


class TrackedShip(db.Model):
    """Model for tracking specific ships of interest."""
    __tablename__ = 'tracked_ships'

    id = db.Column(db.Integer, primary_key=True)
    mmsi = db.Column(db.String(20), db.ForeignKey('ships.mmsi'), nullable=False, unique=True)
    name = db.Column(db.String(100))  # Custom name/alias for the tracked ship
    notes = db.Column(db.Text)  # Optional notes about why this ship is tracked
    added_date = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    added_by = db.Column(db.String(100))  # Who added this ship to tracking

    # Relationship to ship
    ship = db.relationship('Ship', backref='tracking_info')

    def __repr__(self):
        return f'<TrackedShip {self.mmsi}: {self.name or "Unnamed"}>'

    def to_dict(self):
        """Convert tracked ship to dictionary."""
        ship_data = self.ship.to_dict() if self.ship else {}
        return {
            'id': self.id,
            'mmsi': self.mmsi,
            'name': self.name,
            'notes': self.notes,
            'added_date': self.added_date.isoformat(),
            'added_by': self.added_by,
            'ship_data': ship_data
        }