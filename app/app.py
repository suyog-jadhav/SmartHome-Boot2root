"""
SmartHome Lab — Flask application entry point.
"""
import os
import sys
import logging
from flask import Flask, redirect, url_for, render_template

# Ensure blueprints can import siblings
sys.path.insert(0, os.path.dirname(__file__))

from database import initialize_database
from blueprints.auth     import auth_bp
from blueprints.dashboard import dashboard_bp
from blueprints.devices   import devices_bp
from blueprints.admin     import admin_bp

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Secret key generated at startup — not hardcoded
    app.secret_key = os.environ.get("FLASK_SECRET", os.urandom(32))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # ---------------------------------------------------------------------------
    # Security headers (after_request)
    # ---------------------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"]        = "DENY"
        # CSP allows Bootstrap CDN + inline styles for the lab UI
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net;"
        )
        # Clue: hints at template engine without naming the vulnerability
        response.headers["X-Powered-By"] = "Jinja2/3.1"
        return response

    # ---------------------------------------------------------------------------
    # Error handlers
    # ---------------------------------------------------------------------------
    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    # ---------------------------------------------------------------------------
    # Blueprints
    # ---------------------------------------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(admin_bp)

    # ---------------------------------------------------------------------------
    # Root redirect
    # ---------------------------------------------------------------------------
    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    return app


if __name__ == "__main__":
    initialize_database()
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=False)
