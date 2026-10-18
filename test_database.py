"""Simple tests for the database layer (Phase 2).

Run with:  .venv\\Scripts\\python.exe test_database.py
Uses a temporary database file so your real data is never touched.
"""

import os
import tempfile

import database

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
    # Use a temporary file so the real lineage.db is not modified
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db = f.name

    try:
        print("Running database tests...")

        # Test 1: init_db creates the tables
        database.init_db(test_db)
        check("init_db creates tables without error", True)

        # Test 2: add_version + get_versions
        vid = database.add_version("test_source", 1, "first version", db_path=test_db)
        versions = database.get_versions(test_db)
        check("add_version returns an id", vid is not None)
        check("get_versions returns the new version", len(versions) == 1)
        check("version fields are correct",
              versions[0]["source_name"] == "test_source"
              and versions[0]["version_number"] == 1
              and versions[0]["status"] == "active")

        # Test 3: pipeline run linked to a version
        rid = database.add_pipeline_run("test_pipeline", vid, "success", "ok", db_path=test_db)
        runs = database.get_pipeline_runs(test_db)
        check("add_pipeline_run returns an id", rid is not None)
        check("get_pipeline_runs returns the new run", len(runs) == 1)
        check("run links to correct version", runs[0]["version_id"] == vid)

        # Test 4: failure run is stored too
        database.add_pipeline_run("test_pipeline", vid, "failure", "boom", db_path=test_db)
        check("failed runs are stored", len(database.get_pipeline_runs(test_db)) == 2)

        # Test 5: rollback log
        database.add_rollback_log(rid, vid, "test rollback", db_path=test_db)
        logs = database.get_rollback_logs(test_db)
        check("rollback log is stored", len(logs) == 1)

        # Test 6: ordering is newest first
        database.add_version("test_source", 2, "second version", db_path=test_db)
        versions = database.get_versions(test_db)
        check("versions are ordered newest first",
              versions[0]["version_number"] == 2)

        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0

    finally:
        os.unlink(test_db)


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)
