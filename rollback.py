"""Automatic rollback logic (Phase 4).

When a pipeline run fails, the tracker rolls back to the last successful
version of that data source:

  1. Find the newest version that is still 'active' (the last known good one).
  2. Mark the failed version as 'rolled_back'.
  3. Write an entry in rollback_logs explaining what happened and why.

This keeps a full history: nothing is deleted, the bad version simply becomes
inactive and the good version continues to be used.
"""

import os

import database


def _env_flag(name, default):
    """Read a true/false switch from an environment variable.

    Accepts 1/true/yes/on (any case) as True. Anything else is False.
    If the variable is not set at all, `default` is returned.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# Configuration switch: disable by setting AUTO_ROLLBACK_ENABLED=false.
AUTO_ROLLBACK_ENABLED = _env_flag("AUTO_ROLLBACK_ENABLED", True)


def find_last_successful_version(source_name, before_version_id=None, db_path=None):
    """Return the newest usable version for a source, or None if there is none.

    'Usable' means status is 'active'. Failed and already rolled back
    versions are ignored, which is exactly what we want to roll back to.
    """
    candidates = [
        v
        for v in database.get_versions(db_path=db_path)
        if v["source_name"] == source_name
        and v["status"] == "active"
        and (before_version_id is None or v["id"] != before_version_id)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda v: (v["version_number"], v["id"]))


def get_current_version(source_name, db_path=None):
    """Return the version currently in use for a source (None if rolled back fully)."""
    return find_last_successful_version(source_name, db_path=db_path)


def perform_rollback(source_name, failed_run_id, failed_version_id, reason, db_path=None):
    """Roll back a failed version to the last successful one.

    Returns a dictionary describing the outcome. If there is no earlier
    successful version, no rollback is possible and that is reported clearly.
    """
    target = find_last_successful_version(
        source_name, before_version_id=failed_version_id, db_path=db_path
    )

    if target is None:
        # Nothing to restore: the very first run for this source failed.
        database.update_version_status(failed_version_id, "failed", db_path=db_path)
        return {
            "status": "no_target",
            "source_name": source_name,
            "failed_version_id": failed_version_id,
            "restored_version_id": None,
            "message": "No previous successful version to roll back to.",
        }

    # Mark the failed version as rolled back and record the event.
    database.update_version_status(failed_version_id, "rolled_back", db_path=db_path)
    log_id = database.add_rollback_log(
        failed_run_id, target["id"], reason, db_path=db_path
    )

    return {
        "status": "rolled_back",
        "log_id": log_id,
        "source_name": source_name,
        "failed_version_id": failed_version_id,
        "restored_version_id": target["id"],
        "restored_version_number": target["version_number"],
        "message": (
            f"Rolled back to {source_name} v{target['version_number']} "
            f"(version id {target['id']})"
        ),
    }
