from datetime import datetime, timezone
from . import db


class TrackedShip(db.Model):
    """Model for tracking specific ships of interest."""
    __tablename__ = 'tracked_ships'

    id = db.Column(db.Integer, primary_key=True)
    mmsi = db.Column(db.String(20), db.ForeignKey('ships.mmsi'), nullable=False, unique=True)
    name = db.Column(db.String(100))  # Custom name/alias for the tracked ship
    notes = db.Column(db.Text)  # Optional notes about why this ship is tracked
    added_date = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    added_by_user = db.Column(db.Integer, db.ForeignKey('users.id'))  # Link to user
    added_by = db.Column(db.String(100))  # Legacy field for backward compatibility

    # Relationships
    ship = db.relationship('Ship', backref='tracking_info')
    user = db.relationship('User', backref='tracked_ships')

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
            'added_by_user': self.user.full_name if self.user else None,
            'ship_data': ship_data
        }