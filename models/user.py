from datetime import datetime, timezone

# Import db from the main models package
from . import db


class User(db.Model):
    """User authentication model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # admin, company, company_user, user
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Company relationships
    company_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Points to company user
    company_name = db.Column(db.String(200))  # For company role users

    # Self-referential relationships
    company_users = db.relationship('User',
                                    foreign_keys=[company_id],
                                    backref=db.backref('company', remote_side=[id]),
                                    cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}: {self.full_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'company_id': self.company_id,
            'company_name': self.company_name
        }

    def get_tracking_limit(self):
        """Get the tracking limit based on user role"""
        if self.role == 'user':
            return 5  # Free users get 5 ships
        elif self.role in ['company', 'company_user']:
            return None  # Unlimited for company users
        elif self.role == 'admin':
            return None  # Unlimited for admin
        return 0

    def can_track_ship(self):
        """Check if user can track more ships based on role and limits"""
        from .tracked_ship import TrackedShip

        if self.role == 'admin':
            return True, "Admin has unlimited access"

        if self.role == 'company':
            return True, "Company has unlimited tracking"

        if self.role == 'company_user':
            # Company users can track ships assigned to their company
            return True, "Company user access"

        if self.role == 'user':
            # Check current tracking count
            current_count = TrackedShip.query.filter_by(added_by_user_id=self.id).count()
            if current_count >= 5:
                return False, "Free users limited to 5 tracked ships"
            return True, f"Can track {5 - current_count} more ships"

        return False, "No tracking permission"