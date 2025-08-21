from datetime import datetime, timezone
from . import db


class Company(db.Model):
    """Company model for multi-tenant ship management."""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    website = db.Column(db.String(200))
    created_date = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Company settings
    max_tracked_ships = db.Column(db.Integer, default=50)
    timezone = db.Column(db.String(50), default='UTC')

    # Relationships
    users = db.relationship('User', backref='company', lazy='dynamic')
    tracked_ships = db.relationship('TrackedShip', backref='company', lazy='dynamic')

    def __repr__(self):
        return f'<Company {self.name}>'

    def to_dict(self):
        """Convert company to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'website': self.website,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'is_active': self.is_active,
            'max_tracked_ships': self.max_tracked_ships,
            'timezone': self.timezone,
            'user_count': self.users.filter_by(is_active=True).count(),
            'tracked_ships_count': self.tracked_ships.count()
        }