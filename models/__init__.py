from flask_sqlalchemy import SQLAlchemy

# Initialize db here
db = SQLAlchemy()

# Import all models so they're available when you import from models
from .user import User
from .ship import Ship
from .position import Position
from .tracked_ship import TrackedShip

# Make everything available at package level
__all__ = [
    'db',
    'User',
    'Ship',
    'Position',
    'TrackedShip'
]