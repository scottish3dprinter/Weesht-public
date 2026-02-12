import os
import sqlite3

from flask import current_app
from werkzeug.security import generate_password_hash


def getDBconnection():
    dbPath = current_app.config["SQLITE_DB_PATH"]
    connection = sqlite3.connect(dbPath)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initDB(app):
    dbPath = app.config["SQLITE_DB_PATH"]
    dbDir = os.path.dirname(dbPath)
    if dbDir:
        os.makedirs(dbDir, exist_ok=True)

    connection = sqlite3.connect(dbPath)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                level INTEGER,
                email_address TEXT,
                create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_title TEXT NOT NULL,
                username TEXT NOT NULL,
                request_body TEXT NOT NULL,
                resolver_username TEXT,
                create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username),
                FOREIGN KEY (resolver_username) REFERENCES users(username)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                date_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username)
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                message_body TEXT NOT NULL,
                create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES requests(request_id) ON DELETE CASCADE,
                FOREIGN KEY (username) REFERENCES users(username)
            );
            """
        )

        default_admin_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
        default_admin_password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "password")
        password_hash = generate_password_hash(default_admin_password)
        connection.execute(
            """
            INSERT INTO users (username, password_hash, level)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO NOTHING;
            """,
            (default_admin_username, password_hash, 0),
        )
        connection.commit()
    finally:
        connection.close()
