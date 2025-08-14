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


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    AIS_UDP_PORT = 15200


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    AIS_UDP_PORT = 15100


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}