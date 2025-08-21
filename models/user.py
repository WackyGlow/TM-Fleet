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
    role = db.Column(db.String(20), default='viewer', nullable=False)  # viewer, operator, admin, super_admin
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_date = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    tracked_ships_added = db.relationship('TrackedShip', foreign_keys='TrackedShip.added_by_user_id',
                                          backref='added_by_user', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    created_by = db.relationship('User', remote_side=[id], backref='created_users')

    # Indexes for performance
    __table_args__ = (
        Index('idx_users_company_active', 'company_id', 'is_active'),
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
    )

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
        role_hierarchy = {'viewer': 1, 'operator': 2, 'admin': 3, 'super_admin': 4}
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 4)
        return user_level >= required_level