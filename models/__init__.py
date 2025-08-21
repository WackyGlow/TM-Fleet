from flask_sqlalchemy import SQLAlchemy

# Initialize db here
db = SQLAlchemy()

# Import all models in the correct order to avoid circular import issues
from .company import Company
from .user import User
from .ship import Ship
from .position import Position
from .tracked_ship import TrackedShip

# Make everything available at package level
__all__ = [
    'db',
    'Company',
    'User',
    'Ship',
    'Position',
    'TrackedShip'
]