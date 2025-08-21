from datetime import datetime, timezone
from . import db


class Position(db.Model):
    """Current ship position data model - one record per ship."""
    __tablename__ = 'positions'

    mmsi = db.Column(db.String(20), db.ForeignKey('ships.mmsi'), primary_key=True)
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

    # Relationship
    ship = db.relationship('Ship', backref=db.backref('current_position', uselist=False))

    def __repr__(self):
        return f'<Position {self.mmsi}: {self.latitude}, {self.longitude}>'

    def to_dict(self):
        """Convert position to dictionary."""
        return {
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