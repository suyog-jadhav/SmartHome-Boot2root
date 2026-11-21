"""
Auth blueprint — login / logout.
SQLi intentionally preserved in the login query.
"""
import logging
import os
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, abort,
)
from database import get_db

log = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    csrf_token = os.urandom(16).hex()   # decorative — not validated (intentional)

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        connection = get_db()
        # ---- INTENTIONALLY VULNERABLE SQL QUERY (challenge SQLi) ----
        query = (
            "SELECT * FROM users "
            f"WHERE username = '{username}' AND password = '{password}'"
        )
        user = connection.execute(query).fetchone()
        connection.close()

        if user:
            session.clear()
            session["username"] = user["username"]
            session["role"]     = user["role"]
            session["csrf"]     = os.urandom(16).hex()
            log.info("Login success: %s (role=%s)", user["username"], user["role"])
            return redirect(url_for("dashboard.index"))

        log.warning("Login failure for username: %s", username[:64])
        error = "Invalid credentials. Please try again."

    return render_template("auth/login.html", error=error, csrf_token=csrf_token)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password")
def forgot_password():
    # Intentional dead end / decoy
    abort(404)

