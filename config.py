import os


class Config:
    """Base configuration class."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database configuration
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASEDIR, 'ships.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AIS receiver configuration
    AIS_UDP_PORT = int(os.environ.get('AIS_UDP_PORT', 15100))
    AIS_DEV_PORT = int(os.environ.get('AIS_DEV_PORT', 15200))

    # Application settings
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # MULTIPART BUFFER CLEANUP (message-based - still needed)
    CLEANUP_INTERVAL_MESSAGES = int(os.environ.get('CLEANUP_INTERVAL_MESSAGES', 1000))

    # AUTOMATIC DATABASE CLEANUP SETTINGS
    AUTO_CLEANUP_ENABLED = os.environ.get('AUTO_CLEANUP_ENABLED', 'True').lower() == 'true'

    # Age thresholds for cleanup
    POSITION_MAX_AGE_HOURS = float(os.environ.get('POSITION_MAX_AGE_HOURS', 2.0))
    SHIP_MAX_AGE_HOURS = float(os.environ.get('SHIP_MAX_AGE_HOURS', 24.0))

    # Time-based cleanup intervals (in hours)
    AGE_CLEANUP_INTERVAL_HOURS = float(os.environ.get('AGE_CLEANUP_INTERVAL_HOURS', 1.0))  # Every 1 hour
    DUPLICATE_CLEANUP_INTERVAL_HOURS = float(os.environ.get('DUPLICATE_CLEANUP_INTERVAL_HOURS', 6.0))  # Every 6 hours


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    AIS_UDP_PORT = 15200

    # More aggressive cleanup for development
    POSITION_MAX_AGE_HOURS = 1.0  # 1 hour in dev
    SHIP_MAX_AGE_HOURS = 12.0  # 12 hours in dev
    AGE_CLEANUP_INTERVAL_HOURS = 0.5  # Every 30 minutes in dev
    DUPLICATE_CLEANUP_INTERVAL_HOURS = 2.0  # Every 2 hours in dev


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    AIS_UDP_PORT = 15100

    # Conservative cleanup for production
    POSITION_MAX_AGE_HOURS = 2.0  # 2 hours in production
    SHIP_MAX_AGE_HOURS = 48.0  # 48 hours in production
    AGE_CLEANUP_INTERVAL_HOURS = 2.0  # Every 2 hours in production
    DUPLICATE_CLEANUP_INTERVAL_HOURS = 12.0  # Every 12 hours in production


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}