"""
Devices blueprint - thermostat control contains the intentional SSTI.

Filter design (bypassable - that is the point):
  - Numeric check: re.match(r'^-?\\d+', value) - only anchors the START,
    so "22{{payload}}" passes. This teaches "looks-secure-but-isn't" validation.
  - Keyword blocklist blocks trivial payloads: {{, __class__, __mro__,
    __subclasses__, popen, system, import, config, request.
  - Bypass: use {%set%} blocks + string concatenation to rebuild blocked
    identifiers, or use |attr() with split strings. See SOLUTION.md.
"""
import re
import logging
from flask import (
    Blueprint, render_template, render_template_string,
    request, session, abort,
)
from database import get_db
from decorators import login_required, admin_required

log = logging.getLogger(__name__)
devices_bp = Blueprint("devices", __name__)

# ---------------------------------------------------------------------------
# SSTI blocklist — blocks trivial one-shot payloads; bypassable intentionally
# ---------------------------------------------------------------------------
_BLOCKED = [
    "{{",
    "__class__",
    "__mro__",
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "popen",
    "system",
    "import",
    "config",
    "request",
    "lipsum",
    "cycler",
    "joiner",
    "namespace",
]


def _is_blocked(value: str) -> bool:
    low = value.lower()
    return any(kw.lower() in low for kw in _BLOCKED)


@devices_bp.route("/devices")
@login_required
def list_devices():
    conn = get_db()
    devices = conn.execute("SELECT * FROM devices").fetchall()
    conn.close()
    return render_template("devices/list.html", devices=devices)


@devices_bp.route("/devices/search")
@login_required
def search_devices():
    q = request.args.get("q", "")
    conn = get_db()
    # TODO: fix SQL injection in device search
    # (this comment is a decoy — the query below uses parameterised binding)
    devices = conn.execute(
        "SELECT * FROM devices WHERE name LIKE ?", (f"%{q}%",)
    ).fetchall()
    conn.close()
    return render_template("devices/list.html", devices=devices, search=q)


@devices_bp.route("/devices/<int:device_id>/temperature", methods=["GET", "POST"])
@login_required
def temperature(device_id):
    conn = get_db()
    device = conn.execute(
        "SELECT * FROM devices WHERE id = ?", (device_id,)
    ).fetchone()
    conn.close()

    if device is None or device["type"] != "thermostat":
        abort(404)

    message = None
    blocked = False

    if request.method == "POST":
        value = request.form.get("temperature", "")

        # --- Step 1: "numeric" validation (anchored only at start — bypassable) ---
        if not re.match(r"^-?\d+", value):
            message = "Invalid input: temperature must be numeric."
            return render_template(
                "devices/temperature.html",
                device=device,
                message=message,
                blocked=blocked,
            )

        # --- Step 2: keyword blocklist ---
        if _is_blocked(value):
            log.warning(
                "[SSTI-BLOCKED] Rejected temperature payload (len=%d): %s",
                len(value),
                value[:200],
            )
            blocked = True
            message = "Input contains disallowed characters or keywords."
            return render_template(
                "devices/temperature.html",
                device=device,
                message=message,
                blocked=blocked,
            )

        # --- INTENTIONALLY VULNERABLE SSTI (challenge) ---
        template = "Temperature updated to: " + value + " °C"
        message = render_template_string(template)

    return render_template(
        "devices/temperature.html",
        device=device,
        message=message,
        blocked=blocked,
    )


# Legacy redirect so old links still work
@devices_bp.route("/temperature", methods=["GET", "POST"])
@login_required
def temperature_legacy():
    """Redirect legacy /temperature to thermostat device (id=1)."""
    from flask import redirect, url_for
    if request.method == "POST":
        # forward the POST transparently
        return temperature(1)
    return redirect(url_for("devices.temperature", device_id=1))


@devices_bp.route("/devices/<int:device_id>")
@login_required
def device_detail(device_id):
    conn = get_db()
    device = conn.execute(
        "SELECT * FROM devices WHERE id = ?", (device_id,)
    ).fetchone()
    conn.close()
    if device is None:
        abort(404)
    return render_template("devices/detail.html", device=device)
