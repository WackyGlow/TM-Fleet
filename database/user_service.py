from models import db, User
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash


class UserService:
    """Service class for user-related database operations."""

    @staticmethod
    def create_user(username, email, password, role='user', company_id=None,
                    first_name=None, last_name=None, phone=None, created_by_user_id=None):
        """Create a new user."""
        try:
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                return {'success': False, 'message': 'Username already exists'}

            if User.query.filter_by(email=email).first():
                return {'success': False, 'message': 'Email already exists'}

            # Create password hash
            password_hash = generate_password_hash(password)

            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                company_id=company_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                created_by_user_id=created_by_user_id,
                created_date=datetime.now(UTC),
                is_active=True
            )

            db.session.add(user)
            db.session.commit()

            return {'success': True, 'message': 'User created successfully', 'user_id': user.id}

        except Exception as e:
            print(f"❌ Error creating user: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error creating user: {str(e)}'}

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID."""
        try:
            return User.query.get(user_id)
        except Exception as e:
            print(f"❌ Error getting user {user_id}: {e}")
            return None

    @staticmethod
    def get_user_by_username(username):
        """Get user by username."""
        try:
            return User.query.filter_by(username=username).first()
        except Exception as e:
            print(f"❌ Error getting user by username {username}: {e}")
            return None

    @staticmethod
    def get_user_by_email(email):
        """Get user by email."""
        try:
            return User.query.filter_by(email=email).first()
        except Exception as e:
            print(f"❌ Error getting user by email {email}: {e}")
            return None

    @staticmethod
    def update_user(user_id, **kwargs):
        """Update user information."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'message': 'User not found'}

            # Update allowed fields
            allowed_fields = ['first_name', 'last_name', 'phone', 'email', 'role', 'is_active']
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)

            db.session.commit()
            return {'success': True, 'message': 'User updated successfully'}

        except Exception as e:
            print(f"❌ Error updating user {user_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error updating user: {str(e)}'}

    @staticmethod
    def update_last_login(user_id):
        """Update user's last login timestamp."""
        try:
            user = User.query.get(user_id)
            if user:
                user.last_login = datetime.now(UTC)
                db.session.commit()
        except Exception as e:
            print(f"❌ Error updating last login for user {user_id}: {e}")
            db.session.rollback()

    @staticmethod
    def deactivate_user(user_id):
        """Deactivate a user account."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'message': 'User not found'}

            user.is_active = False
            db.session.commit()
            return {'success': True, 'message': 'User deactivated successfully'}

        except Exception as e:
            print(f"❌ Error deactivating user {user_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error deactivating user: {str(e)}'}

    @staticmethod
    def activate_user(user_id):
        """Activate a user account."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'message': 'User not found'}

            user.is_active = True
            db.session.commit()
            return {'success': True, 'message': 'User activated successfully'}

        except Exception as e:
            print(f"❌ Error activating user {user_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error activating user: {str(e)}'}

    @staticmethod
    def get_users_by_company(company_id, include_inactive=False):
        """Get all users for a company."""
        try:
            query = User.query.filter_by(company_id=company_id)

            if not include_inactive:
                query = query.filter_by(is_active=True)

            users = query.all()
            return [user.to_dict() for user in users]

        except Exception as e:
            print(f"❌ Error getting users for company {company_id}: {e}")
            return []

    @staticmethod
    def get_users_by_role(role, company_id=None):
        """Get users by role, optionally filtered by company."""
        try:
            query = User.query.filter_by(role=role, is_active=True)

            if company_id:
                query = query.filter_by(company_id=company_id)

            users = query.all()
            return [user.to_dict() for user in users]

        except Exception as e:
            print(f"❌ Error getting users by role {role}: {e}")
            return []

    @staticmethod
    def change_password(user_id, new_password):
        """Change user password."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'message': 'User not found'}

            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            return {'success': True, 'message': 'Password changed successfully'}

        except Exception as e:
            print(f"❌ Error changing password for user {user_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error changing password: {str(e)}'}

    @staticmethod
    def get_user_stats(user_id):
        """Get statistics for a specific user."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}

            from models import TrackedShip

            stats = {
                'user_id': user_id,
                'role': user.role,
                'company_id': user.company_id,
                'is_active': user.is_active,
                'created_date': user.created_date.isoformat() if user.created_date else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            }

            # Add role-specific stats
            if user.role == 'user':
                # Free user stats
                tracked_count = TrackedShip.query.filter_by(added_by_user_id=user_id).count()
                stats.update({
                    'tracked_ships': tracked_count,
                    'tracking_limit': 5,
                    'remaining_slots': max(0, 5 - tracked_count),
                    'can_track_more': tracked_count < 5
                })
            elif user.role in ['company', 'admin']:
                # Company/admin stats
                if user.company_id:
                    company_tracked = TrackedShip.query.filter_by(company_id=user.company_id).count()
                    stats.update({
                        'company_tracked_ships': company_tracked,
                        'tracking_limit': None,  # Unlimited
                        'can_track_more': True
                    })

            return stats

        except Exception as e:
            print(f"❌ Error getting user stats for {user_id}: {e}")
            return {}