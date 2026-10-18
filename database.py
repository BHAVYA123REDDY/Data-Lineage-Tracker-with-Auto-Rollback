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

            CREATE TABLE IF NOT EXISTS lineage_nodes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                node_type   TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lineage_edges (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node_id INTEGER NOT NULL,
                to_node_id   INTEGER NOT NULL,
                step_name    TEXT,
                created_at   TEXT    NOT NULL,
                FOREIGN KEY (from_node_id) REFERENCES lineage_nodes(id),
                FOREIGN KEY (to_node_id)   REFERENCES lineage_nodes(id)
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


def get_version_by_id(version_id, db_path=None):
    """Return one version as a dictionary, or None if not found."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM data_versions WHERE id = ?", (version_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_latest_version(source_name, only_successful=False, db_path=None):
    """Return the newest version for a source, or None."""
    conn = get_connection(db_path)
    try:
        sql = ("SELECT * FROM data_versions WHERE source_name = ?")
        params = [source_name]
        if only_successful:
            sql += " AND status = 'active'"
        sql += " ORDER BY version_number DESC, id DESC LIMIT 1"
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_version_status(version_id, status, db_path=None):
    """Change the status of a version (e.g. 'active' -> 'failed')."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE data_versions SET status = ? WHERE id = ?", (status, version_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_source_names(db_path=None):
    """Return the distinct list of tracked data sources."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT source_name FROM data_versions ORDER BY source_name"
        ).fetchall()
        return [row["source_name"] for row in rows]
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


def get_pipeline_runs_detailed(limit=None, db_path=None):
    """Pipeline runs joined with the version and source they belong to."""
    conn = get_connection(db_path)
    try:
        sql = """
            SELECT r.id, r.pipeline_name, r.version_id, r.status, r.message,
                   r.started_at, r.finished_at,
                   v.source_name, v.version_number, v.status AS version_status
            FROM pipeline_runs r
            LEFT JOIN data_versions v ON v.id = r.version_id
            ORDER BY r.id DESC
        """
        params = []
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
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


def get_rollback_logs_detailed(limit=None, db_path=None):
    """Rollback events joined with the failed run and the restored version."""
    conn = get_connection(db_path)
    try:
        sql = """
            SELECT rb.id, rb.failed_run_id, rb.rolled_back_to_version_id,
                   rb.reason, rb.created_at,
                   r.pipeline_name,
                   COALESCE(failed.source_name, restored.source_name) AS source_name,
                   failed.version_number AS failed_version_number,
                   restored.version_number AS restored_version_number
            FROM rollback_logs rb
            LEFT JOIN pipeline_runs r     ON r.id = rb.failed_run_id
            LEFT JOIN data_versions failed   ON failed.id = r.version_id
            LEFT JOIN data_versions restored ON restored.id = rb.rolled_back_to_version_id
            ORDER BY rb.id DESC
        """
        params = []
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------- lineage (Phase 3) ----------------------

def add_lineage_node(name, node_type, description="", db_path=None):
    """Insert a lineage node (node_type: 'source', 'step' or 'output')."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO lineage_nodes (name, node_type, description, created_at) "
            "VALUES (?, ?, ?, ?)",
            (name, node_type, description, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_lineage_nodes(db_path=None):
    """Return all lineage nodes ordered by type then name."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM lineage_nodes ORDER BY node_type, name"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def find_lineage_node(name, db_path=None):
    """Return a lineage node by its name, or None."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM lineage_nodes WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_lineage_edge(from_node_id, to_node_id, step_name="", db_path=None):
    """Connect two lineage nodes with a directed edge."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO lineage_edges (from_node_id, to_node_id, step_name, created_at) "
            "VALUES (?, ?, ?, ?)",
            (from_node_id, to_node_id, step_name, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_lineage_edges(db_path=None):
    """Return all lineage edges together with the node names they connect."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT e.id, e.step_name,
                   f.name AS from_name, f.node_type AS from_type,
                   t.name AS to_name,   t.node_type AS to_type
            FROM lineage_edges e
            JOIN lineage_nodes f ON f.id = e.from_node_id
            JOIN lineage_nodes t ON t.id = e.to_node_id
            ORDER BY e.id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
