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

    # Cleanup settings
    CLEANUP_INTERVAL_MESSAGES = int(os.environ.get('CLEANUP_INTERVAL_MESSAGES', 1000))
    DB_CLEANUP_INTERVAL_MESSAGES = int(os.environ.get('DB_CLEANUP_INTERVAL_MESSAGES', 10000))
    DB_CLEANUP_DAYS = int(os.environ.get('DB_CLEANUP_DAYS', 7))

    # Status-based position cleanup settings
    STATUS_CLEANUP_INTERVAL_MESSAGES = int(os.environ.get('STATUS_CLEANUP_INTERVAL_MESSAGES', 5000))
    SAILING_POSITION_TIMEOUT_MINUTES = int(os.environ.get('SAILING_POSITION_TIMEOUT_MINUTES', 2))
    MOORED_POSITION_TIMEOUT_HOURS = int(os.environ.get('MOORED_POSITION_TIMEOUT_HOURS', 1))

    # Enable/disable automatic status-based cleanup
    ENABLE_STATUS_CLEANUP = os.environ.get('ENABLE_STATUS_CLEANUP', 'True').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    AIS_UDP_PORT = 15200

    # More frequent cleanup in development for testing
    STATUS_CLEANUP_INTERVAL_MINUTES = 2  # Every 2 minutes in dev
    UNDERWAY_POSITION_TIMEOUT_MINUTES = 1  # 1 minute for testing
    MOORED_POSITION_TIMEOUT_HOURS = 1  # 1 hour


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    AIS_UDP_PORT = 15100

    # Production cleanup settings
    STATUS_CLEANUP_INTERVAL_MINUTES = 5  # Every 5 minutes
    UNDERWAY_POSITION_TIMEOUT_MINUTES = 2
    MOORED_POSITION_TIMEOUT_HOURS = 2


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}