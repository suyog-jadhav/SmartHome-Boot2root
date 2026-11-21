"""
Admin blueprint — system status, activity log management.
All routes require admin role.
"""
import logging
from flask import Blueprint, render_template, jsonify, request, abort, session
from database import get_db
from decorators import admin_required

log = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def index():
    conn = get_db()
    users   = conn.execute("SELECT id, username, role FROM users").fetchall()
    devices = conn.execute("SELECT * FROM devices").fetchall()
    logs    = conn.execute(
        "SELECT * FROM activity_log ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return render_template(
        "admin/index.html",
        users=users, devices=devices, logs=logs,
    )


@admin_bp.route("/admin/status")
@admin_required
def status():
    """
    System status page — deliberately leaks clues:
    - 'legacy OpenSSH build, scheduled for upgrade'
    - cron job running every minute against /opt/maintenance.sh
    """
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM activity_log ORDER BY id DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return render_template("admin/status.html", logs=logs)


# ---------------------------------------------------------------------------
# Decoy endpoints
# ---------------------------------------------------------------------------

@admin_bp.route("/api/debug")
@admin_required
def api_debug():
    """
    Decoy — returns a convincing but useless fake config blob.
    No real secrets exposed.
    """
    log.warning(
        "[DECOY] /api/debug hit by user=%s ip=%s",
        session.get("username", "?"),
        request.remote_addr,
    )
    fake = {
        "app":    "SmartHome Gateway",
        "build":  "2.4.1-prod",
        "db":     "sqlite:///smarthome.db",
        "mqtt":   "mqtt://10.0.0.1:1883",
        "secret": "REDACTED",
        "debug":  False,
        "env":    "production",
    }
    return jsonify(fake)


@admin_bp.route("/backup.zip")
def backup_zip():
    """
    Decoy — returns a convincing 404-looking response.
    Logs the hit so the lab host knows someone found it.
    """
    log.warning(
        "[DECOY] /backup.zip probed by ip=%s", request.remote_addr
    )
    abort(404)

