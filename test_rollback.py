"""Tests for automatic rollback (Phase 4).

Run with:  .venv\\Scripts\\python.exe test_rollback.py
Uses a temporary database file so your real data is never touched.
"""

import os
import tempfile

import database
import pipeline
import rollback

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")


def run_tests():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db = f.name

    try:
        print("Running automatic rollback tests...")
        database.init_db(test_db)
        source = "customers_csv"

        # --- 1. Failure on the very first run: nothing to roll back to ---
        first = pipeline.simulate_pipeline_run(source, force_failure=True, db_path=test_db)
        check("first failure reports no rollback target", first["rollback"]["status"] == "no_target")
        check("first failed version stays 'failed'",
              database.get_version_by_id(first["version_id"], test_db)["status"] == "failed")
        check("no rollback log written for first failure",
              len(database.get_rollback_logs(test_db)) == 0)

        # --- 2. Now a successful run (v2) becomes the good version ---
        good = pipeline.simulate_pipeline_run(source, failure_probability=0.0, db_path=test_db)
        check("successful run is active",
              database.get_version_by_id(good["version_id"], test_db)["status"] == "active")
        check("no rollback on success", good["rollback"] is None)

        # --- 3. Another success (v3), then a failure (v4) triggers rollback ---
        good2 = pipeline.simulate_pipeline_run(source, failure_probability=0.0, db_path=test_db)
        check("second success is v3", good2["version_number"] == 3)

        bad = pipeline.simulate_pipeline_run(source, force_failure=True, db_path=test_db)
        check("failure reports rolled_back", bad["rollback"]["status"] == "rolled_back")
        check("failed version marked rolled_back",
              database.get_version_by_id(bad["version_id"], test_db)["status"] == "rolled_back")
        check("rollback restored the newest good version (v3)",
              bad["rollback"]["restored_version_id"] == good2["version_id"])
        check("failure response says rolled_back is True", bad["rolled_back"] is True)

        # --- 4. Rollback is recorded in history ---
        logs = database.get_rollback_logs(test_db)
        check("one rollback log recorded", len(logs) == 1)
        check("rollback log points to the failed run", logs[0]["failed_run_id"] == bad["run_id"])
        check("rollback log points to v3", logs[0]["rolled_back_to_version_id"] == good2["version_id"])
        check("rollback log has a reason", bool(logs[0]["reason"]))

        # --- 5. Current version in use is the restored one ---
        current = rollback.get_current_version(source, test_db)
        check("current version is v3 after rollback", current["id"] == good2["version_id"])

        # --- 6. Version numbering continues after a rollback ---
        after = pipeline.simulate_pipeline_run(source, failure_probability=0.0, db_path=test_db)
        check("numbering continues after rollback (v5)", after["version_number"] == 5)
        check("new success becomes the current version",
              rollback.get_current_version(source, test_db)["id"] == after["version_id"])

        # --- 7. Manual rollback endpoint logic ---
        manual = rollback.perform_rollback(
            source,
            failed_run_id=None,
            failed_version_id=after["version_id"],
            reason="manual test",
            db_path=test_db,
        )
        check("manual rollback works", manual["status"] == "rolled_back")
        check("manual rollback created a second log",
              len(database.get_rollback_logs(test_db)) == 2)

        # --- 8. Config switch exists ---
        check("auto rollback is enabled by default", rollback.AUTO_ROLLBACK_ENABLED is True)

        # --- 9. Latest successful lookup ignores failed/rolled_back versions ---
        target = rollback.find_last_successful_version(source, db_path=test_db)
        check("rollback target is always an active version", target["status"] == "active")

        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0

    finally:
        os.unlink(test_db)


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)
