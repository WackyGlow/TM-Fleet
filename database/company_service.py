from models import db, Company, User, TrackedShip
from datetime import datetime, UTC


class CompanyService:
    """Service class for company-related database operations."""

    @staticmethod
    def create_company(name, email, phone=None, address=None, website=None,
                       max_tracked_ships=50, timezone='UTC'):
        """Create a new company."""
        try:
            # Check if company already exists
            if Company.query.filter_by(email=email).first():
                return {'success': False, 'message': 'Company email already exists'}

            # Create company
            company = Company(
                name=name,
                email=email,
                phone=phone,
                address=address,
                website=website,
                max_tracked_ships=max_tracked_ships,
                timezone=timezone,
                created_date=datetime.now(UTC),
                is_active=True
            )

            db.session.add(company)
            db.session.commit()

            return {'success': True, 'message': 'Company created successfully', 'company_id': company.id}

        except Exception as e:
            print(f"❌ Error creating company: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error creating company: {str(e)}'}

    @staticmethod
    def get_company_by_id(company_id):
        """Get company by ID."""
        try:
            return Company.query.get(company_id)
        except Exception as e:
            print(f"❌ Error getting company {company_id}: {e}")
            return None

    @staticmethod
    def get_company_by_email(email):
        """Get company by email."""
        try:
            return Company.query.filter_by(email=email).first()
        except Exception as e:
            print(f"❌ Error getting company by email {email}: {e}")
            return None

    @staticmethod
    def update_company(company_id, **kwargs):
        """Update company information."""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {'success': False, 'message': 'Company not found'}

            # Update allowed fields
            allowed_fields = ['name', 'email', 'phone', 'address', 'website',
                              'max_tracked_ships', 'timezone', 'is_active']
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(company, field):
                    setattr(company, field, value)

            db.session.commit()
            return {'success': True, 'message': 'Company updated successfully'}

        except Exception as e:
            print(f"❌ Error updating company {company_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error updating company: {str(e)}'}

    @staticmethod
    def get_all_companies(include_inactive=False):
        """Get all companies."""
        try:
            query = Company.query

            if not include_inactive:
                query = query.filter_by(is_active=True)

            companies = query.all()
            return [company.to_dict() for company in companies]

        except Exception as e:
            print(f"❌ Error getting companies: {e}")
            return []

    @staticmethod
    def deactivate_company(company_id):
        """Deactivate a company."""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {'success': False, 'message': 'Company not found'}

            company.is_active = False
            db.session.commit()
            return {'success': True, 'message': 'Company deactivated successfully'}

        except Exception as e:
            print(f"❌ Error deactivating company {company_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error deactivating company: {str(e)}'}

    @staticmethod
    def activate_company(company_id):
        """Activate a company."""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {'success': False, 'message': 'Company not found'}

            company.is_active = True
            db.session.commit()
            return {'success': True, 'message': 'Company activated successfully'}

        except Exception as e:
            print(f"❌ Error activating company {company_id}: {e}")
            db.session.rollback()
            return {'success': False, 'message': f'Error activating company: {str(e)}'}

    @staticmethod
    def get_company_stats(company_id):
        """Get comprehensive statistics for a company."""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {}

            # Get user counts by role
            all_users = User.query.filter_by(company_id=company_id, is_active=True).all()
            user_counts = {}
            for role in ['admin', 'company', 'company_user', 'user']:
                user_counts[f'{role}_users'] = len([u for u in all_users if u.role == role])

            # Get tracked ships count
            tracked_ships_count = TrackedShip.query.filter_by(company_id=company_id).count()

            # Get active tracked ships (ships seen in last hour)
            from datetime import timedelta
            from models import Ship
            cutoff = datetime.now(UTC) - timedelta(hours=1)

            active_tracked_ships = db.session.query(TrackedShip).join(Ship).filter(
                TrackedShip.company_id == company_id,
                Ship.last_seen > cutoff
            ).count()

            stats = {
                'company_id': company_id,
                'company_name': company.name,
                'total_users': len(all_users),
                'tracked_ships': tracked_ships_count,
                'active_tracked_ships': active_tracked_ships,
                'max_tracked_ships': company.max_tracked_ships,
                'tracking_usage_percent': (
                            tracked_ships_count / company.max_tracked_ships * 100) if company.max_tracked_ships else 0,
                'can_track_more': tracked_ships_count < company.max_tracked_ships if company.max_tracked_ships else True,
                **user_counts
            }

            return stats

        except Exception as e:
            print(f"❌ Error getting company stats for {company_id}: {e}")
            return {}

    @staticmethod
    def get_company_user_count(user_id):
        """Get count of users in the same company as the given user."""
        try:
            user = User.query.get(user_id)
            if not user or not user.company:
                return 0

            return user.company.users.filter_by(is_active=True).count()
        except Exception as e:
            print(f"❌ Error getting company user count: {e}")
            return 0

    @staticmethod
    def check_company_tracking_limit(company_id):
        """Check if company can track more ships."""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {'can_track': False, 'message': 'Company not found'}

            if company.max_tracked_ships is None:
                return {'can_track': True, 'message': 'Unlimited tracking'}

            current_count = TrackedShip.query.filter_by(company_id=company_id).count()

            if current_count >= company.max_tracked_ships:
                return {
                    'can_track': False,
                    'message': f'Company has reached tracking limit of {company.max_tracked_ships} ships'
                }

            remaining = company.max_tracked_ships - current_count
            return {
                'can_track': True,
                'message': f'Can track {remaining} more ships',
                'remaining': remaining,
                'current': current_count,
                'limit': company.max_tracked_ships
            }

        except Exception as e:
            print(f"❌ Error checking company tracking limit: {e}")
            return {'can_track': False, 'message': f'Error checking limit: {str(e)}'}

    @staticmethod
    def get_default_company():
        """Get the default company (ID=1) or create it if it doesn't exist."""
        try:
            default_company = Company.query.get(1)
            if not default_company:
                # Create default company
                result = CompanyService.create_company(
                    name='Tee Marine ApS',
                    email='info@teemarine.dk',
                    phone='+45 XX XX XX XX',
                    address='Esbjerg, Denmark',
                    website='https://teemarine.dk'
                )
                if result['success']:
                    default_company = Company.query.get(result['company_id'])

            return default_company

        except Exception as e:
            print(f"❌ Error getting/creating default company: {e}")
            return None