from flask import render_template, session, redirect, url_for
from auth import login_required, role_required
from database import AISDatabase


def register_dashboard_routes(app):
    """Register all dashboard routes"""

    @app.route('/admin/dashboard')
    @role_required('system_admin')
    def admin_dashboard():
        """Admin dashboard - full system overview"""
        stats = AISDatabase.get_database_stats()
        # TODO: Add recent activities, user management stats, etc.

        return render_template('dashboards/admin.html',
                               stats=stats,
                               user_role='admin')

    @app.route('/company/dashboard')
    @role_required('manage_company_ships')
    def company_dashboard():
        """Company dashboard - company ship management"""
        user_id = session.get('user_id')

        # Get company's tracked ships
        tracked_ships = AISDatabase.get_company_tracked_ships(user_id)

        # Get company statistics
        company_stats = {
            'tracked_ships': len(tracked_ships),
            'active_ships': len([s for s in tracked_ships if s.get('is_active', False)]),
            'company_users': AISDatabase.get_company_user_count(user_id)
        }

        return render_template('dashboards/company.html',
                               stats=company_stats,
                               tracked_ships=tracked_ships,
                               user_role='company')

    @app.route('/company-user/dashboard')
    @role_required('view_company_ships')
    def company_user_dashboard():
        """Company user dashboard - assigned ships only"""
        user_id = session.get('user_id')

        # Get ships assigned to this company user
        assigned_ships = AISDatabase.get_user_assigned_ships(user_id)

        user_stats = {
            'assigned_ships': len(assigned_ships),
            'active_ships': len([s for s in assigned_ships if s.get('is_active', False)])
        }

        return render_template('dashboards/company_user.html',
                               stats=user_stats,
                               assigned_ships=assigned_ships,
                               user_role='company_user')

    @app.route('/user/dashboard')
    @role_required('track_limited')
    def user_dashboard():
        """Free user dashboard - limited tracking"""
        user_id = session.get('user_id')

        # Get user's tracked ships
        user_tracked_ships = AISDatabase.get_user_tracked_ships(user_id)

        # Get tracking limits
        from models import User
        user = User.query.get(user_id)
        can_track, message = user.can_track_ship()

        user_stats = {
            'tracked_ships': len(user_tracked_ships),
            'tracking_limit': user.get_tracking_limit(),
            'remaining_slots': max(0, 5 - len(user_tracked_ships)),
            'can_track_more': can_track
        }

        return render_template('dashboards/user.html',
                               stats=user_stats,
                               tracked_ships=user_tracked_ships,
                               tracking_message=message,
                               user_role='user')

    @app.route('/dashboard')
    @login_required
    def dashboard_redirect():
        """Main dashboard route - redirects to appropriate role dashboard"""
        user_role = session.get('user_role')

        if user_role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_role == 'company':
            return redirect(url_for('company_dashboard'))
        elif user_role == 'company_user':
            return redirect(url_for('company_user_dashboard'))
        elif user_role == 'user':
            return redirect(url_for('user_dashboard'))
        else:
            # Fallback to map view
            return redirect(url_for('map_view'))