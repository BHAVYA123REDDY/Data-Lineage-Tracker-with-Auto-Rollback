"""Database layer for Data Lineage Tracker (Phase 2).

Uses Python's built-in sqlite3 module - no extra dependencies needed.
Tables:
  - data_versions : stores every version of the tracked data
  - pipeline_runs : stores every pipeline run (success or failure)
  - rollback_logs : stores automatic rollback events (used in Phase 4)
"""

import os
import sqlite3
from datetime import datetime

# Database file lives next to this file, inside the project folder.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineage.db")


def get_connection(db_path=None):
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dictionaries
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    """Create tables if they do not already exist."""
    conn = get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS data_versions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name    TEXT    NOT NULL,
                version_number INTEGER NOT NULL,
                description    TEXT,
                status         TEXT    NOT NULL DEFAULT 'active',
                created_at     TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_name TEXT    NOT NULL,
                version_id    INTEGER,
                status        TEXT    NOT NULL,
                message       TEXT,
                started_at    TEXT    NOT NULL,
                finished_at   TEXT,
                FOREIGN KEY (version_id) REFERENCES data_versions(id)
            );

            CREATE TABLE IF NOT EXISTS rollback_logs (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                failed_run_id           INTEGER,
                rolled_back_to_version_id INTEGER,
                reason                  TEXT,
                created_at              TEXT    NOT NULL,
                FOREIGN KEY (failed_run_id) REFERENCES pipeline_runs(id),
                FOREIGN KEY (rolled_back_to_version_id) REFERENCES data_versions(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _now():
    """Return the current time as a readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------- data_versions ----------------------

def add_version(source_name, version_number, description="", status="active", db_path=None):
    """Insert a new data version and return its id."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO data_versions (source_name, version_number, description, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (source_name, version_number, description, status, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_versions(db_path=None):
    """Return all data versions, newest first."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM data_versions ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------- pipeline_runs ----------------------

def add_pipeline_run(pipeline_name, version_id, status, message="", db_path=None):
    """Insert a pipeline run (status: 'success' or 'failure') and return its id."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO pipeline_runs (pipeline_name, version_id, status, message, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (pipeline_name, version_id, status, message, _now(), _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_pipeline_runs(db_path=None):
    """Return all pipeline runs, newest first."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY started_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------- rollback_logs ----------------------

def add_rollback_log(failed_run_id, rolled_back_to_version_id, reason, db_path=None):
    """Insert a rollback event and return its id (used in Phase 4)."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO rollback_logs (failed_run_id, rolled_back_to_version_id, reason, created_at) "
            "VALUES (?, ?, ?, ?)",
            (failed_run_id, rolled_back_to_version_id, reason, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_rollback_logs(db_path=None):
    """Return all rollback events, newest first."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM rollback_logs ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
