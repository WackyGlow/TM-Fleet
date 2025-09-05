# database/__init__.py
from .init_db import InitMixin
from .ships import ShipMixin
from .positions import PositionMixin
from .cleanup import CleanupMixin
from .stats import StatsMixin

class AISDatabase(
    InitMixin,
    ShipMixin,
    PositionMixin,
    CleanupMixin,
    StatsMixin,
):
    """Database service layer for AIS operations (facade over mixins)."""
    pass

__all__ = ["AISDatabase"]
