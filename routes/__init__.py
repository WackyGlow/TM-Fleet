from .view_routes import register_view_routes
from .api_routes import register_api_routes
from .debug_routes import register_debug_routes
from .cleanup_routes import register_cleanup_routes


def register_routes(app):
    """Register all application routes."""
    register_view_routes(app)
    register_api_routes(app)
    register_debug_routes(app)
    register_cleanup_routes(app)


# Make the main function available at package level
__all__ = ['register_routes']