from datetime import datetime, timezone
from . import db
from sqlalchemy import Index


class User(db.Model):
    """User model with company association and role-based access."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # User profile
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))

    # Company association
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    # Role and permissions
    role = db.Column(db.String(20), default='user', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_date = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    created_by = db.relationship('User', remote_side=[id], backref='created_users')

    def __repr__(self):
        return f'<User {self.username} ({self.company.name if self.company else "No Company"})>'

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'role': self.role,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_by_username': self.created_by.username if self.created_by else None
        }

    @property
    def full_name(self):
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def has_permission(self, required_role):
        """Check if user has required role permission."""
        role_hierarchy = {'user': 1, 'company_user': 2, 'company': 3, 'admin': 4}
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 4)
        return user_level >= required_level

    def can_track_ship(self):
        """Check if user can track more ships based on their role and current count."""
        if self.role in ['admin', 'company']:
            return True, "Unlimited tracking available"

        if self.role == 'company_user':
            return False, "Company users can only view assigned ships"

        # Free users (role='user') have a limit of 5 ships
        from .tracked_ship import TrackedShip
        current_count = TrackedShip.query.filter_by(added_by_user_id=self.id).count()
        limit = self.get_tracking_limit()

        if current_count >= limit:
            return False, f"You've reached your limit of {limit} tracked ships. Upgrade for unlimited tracking."

        remaining = limit - current_count
        return True, f"You can track {remaining} more ship{'s' if remaining != 1 else ''}."

    def get_tracking_limit(self):
        """Get the tracking limit for this user."""
        if self.role in ['admin', 'company']:
            return None  # Unlimited
        elif self.role == 'company_user':
            return None  # No personal tracking, only assigned ships
        else:  # role == 'user'
            return 5  # Free tier limit