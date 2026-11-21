"""
Shared auth decorators.
"""
from functools import wraps
from flask import session, abort


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            abort(401)
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            abort(401)
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated

