"""
Dashboard blueprint.
"""
from flask import Blueprint, render_template, session
from database import get_db
from decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    conn = get_db()
    devices = conn.execute("SELECT * FROM devices").fetchall()
    logs    = conn.execute(
        "SELECT * FROM activity_log ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return render_template(
        "dashboard/index.html",
        devices=devices,
        logs=logs,
        username=session["username"],
        role=session["role"],
    )

