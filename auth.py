# auth.py - Enhanced with role-based permissions
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime, timezone

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# User roles
ROLES = {
    'admin': 'Administrator',
    'company': 'Company',
    'company_user': 'Company User',
    'user': 'User'
}

# Role permissions
ROLE_PERMISSIONS = {
    'admin': ['view_all', 'manage_ships', 'manage_users', 'system_admin', 'manage_companies'],
    'company': ['view_all', 'manage_company_ships', 'track_unlimited', 'manage_company_users', 'view_company_data'],
    'company_user': ['view_company_ships', 'track_company_ships', 'view_assigned_ships'],
    'user': ['view_ships', 'track_limited']  # Limited to 5 ships
}


def login_required(f):
    """Decorator to require login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(required_permission):
    """Decorator to require specific role permission"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))

            user_role = session.get('user_role')
            if not user_role or required_permission not in ROLE_PERMISSIONS.get(user_role, []):
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('index'))  # Redirect to main page

            return f(*args, **kwargs)

        return decorated_function

    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        from models import User
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Account is disabled. Contact administrator.', 'error')
                return render_template('auth/login.html')

            # Store user info in session
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            session['full_name'] = user.full_name

            # Update last login
            user.last_login = datetime.now(timezone.utc)
            from models import db
            db.session.commit()

            flash(f'Welcome back, {user.full_name}!', 'success')

            # Role-based redirect
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'company':
                return redirect(url_for('company_dashboard'))
            elif user.role == 'company_user':
                return redirect(url_for('company_user_dashboard'))
            else:  # user
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    from models import User
    user = User.query.get(session['user_id'])
    return render_template('auth/profile.html', user=user, roles=ROLES)


# Helper functions for templates
def has_permission(permission):
    """Check if current user has permission"""
    if 'user_role' not in session:
        return False
    user_role = session['user_role']
    return permission in ROLE_PERMISSIONS.get(user_role, [])


def get_user_role_name():
    """Get current user's role name"""
    user_role = session.get('user_role')
    return ROLES.get(user_role, 'Unknown')


# Make functions available in templates
@auth_bp.app_context_processor
def inject_auth_functions():
    """Make auth info and functions available in all templates"""
    return dict(
        has_permission=has_permission,
        get_user_role_name=get_user_role_name,
        current_user_id=session.get('user_id'),
        current_username=session.get('username'),
        current_user_full_name=session.get('full_name'),
        current_user_role=session.get('user_role'),
        ROLES=ROLES
    )