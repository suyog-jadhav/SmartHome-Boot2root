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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            temperature INTEGER NOT NULL
        )
    """)

    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "SmartHomeAdmin123", "admin")
    )

    cursor.execute(
        "INSERT OR IGNORE INTO devices (name, temperature) VALUES (?, ?)",
        ("Living Room", 24)
    )

    connection.commit()
    connection.close()
