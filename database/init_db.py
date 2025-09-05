from models import db

class InitMixin:
    @staticmethod
    def init_database(app):
        """Initialize database with Flask app context."""
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")