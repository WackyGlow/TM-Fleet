from flask import render_template


def register_view_routes(app):
    """Register HTML view routes."""

    @app.route("/")
    def index():
        """Main map view."""
        return render_template("map.html")

    @app.route("/track")
    def track_ships():
        """Track ships management page."""
        return render_template("trackships.html")

    @app.route("/info")
    def info():
        """Information page."""
        return render_template("info.html")