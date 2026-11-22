"""
SmartHome Lab — database bootstrap.
"""
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "smarthome.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'user'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            type     TEXT    NOT NULL DEFAULT 'generic',
            room     TEXT    NOT NULL DEFAULT 'Unknown',
            status   TEXT    NOT NULL DEFAULT 'online',
            value    TEXT    NOT NULL DEFAULT '0',
            fw_ver   TEXT    NOT NULL DEFAULT '1.0.0'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL DEFAULT (datetime('now')),
            source    TEXT    NOT NULL,
            message   TEXT    NOT NULL
        )
    """)

    # --- users ---
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "SmartHomeAdmin123!", "admin"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("guest", "guest123", "user"),
    )

    # --- devices ---
    devices = [
        # (name, type, room, status, value, fw_ver)
        ("Living Room Thermostat", "thermostat", "Living Room", "online", "22", "2.1.4"),
        ("Front Door Lock",        "lock",       "Entrance",    "online", "locked", "1.9.2"),
        ("Kitchen Lights",         "light",      "Kitchen",     "online", "on",     "3.0.1"),
        ("Automation Hub",         "hub",        "Server Room", "online", "active", "2.0.0"),
        ("Garage Camera",          "camera",     "Garage",      "online", "streaming", "v0.9.7-RC2"),
        ("Bedroom Lights",         "light",      "Bedroom",     "off",    "off",    "3.0.1"),
        ("Back Door Lock",         "lock",       "Entrance",    "online", "locked", "1.9.2"),
    ]
    for d in devices:
        cursor.execute(
            "INSERT OR IGNORE INTO devices (name, type, room, status, value, fw_ver) VALUES (?,?,?,?,?,?)",
            d,
        )

    # --- initial activity log entries ---
    log_entries = [
        ("system",     "SmartHome platform started — version 2.4.1"),
        ("cron",       "Scheduled maintenance: running /opt/maintenance.sh"),
        ("automation", "automation service account: routine device poll completed"),
        ("system",     "OpenSSH daemon started (legacy build — upgrade scheduled Q1)"),
        ("cron",       "Scheduled maintenance: running /opt/maintenance.sh"),
        ("auth",       "Login attempt from 192.168.1.42 — success (admin)"),
        ("cron",       "Scheduled maintenance: running /opt/maintenance.sh"),
        ("system",     "Temperature setpoint updated for Living Room Thermostat"),
        ("automation", "automation: syncing device state to cloud backup"),
        ("cron",       "Scheduled maintenance: running /opt/maintenance.sh"),
    ]
    cursor.execute("SELECT COUNT(*) FROM activity_log")
    if cursor.fetchone()[0] == 0:
        for src, msg in log_entries:
            cursor.execute(
                "INSERT INTO activity_log (source, message) VALUES (?, ?)", (src, msg)
            )

    connection.commit()
    connection.close()
