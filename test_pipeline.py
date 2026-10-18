"""Tests for lineage tracking and pipeline simulation (Phase 3).

Run with:  .venv\\Scripts\\python.exe test_pipeline.py
Uses a temporary database file so your real data is never touched.
"""

import os
import tempfile

import database
import pipeline

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
        print("Running lineage + pipeline tests...")
        database.init_db(test_db)

        sources = ["customers_csv", "orders_api"]

        # --- lineage building ---
        created = pipeline.initialize_lineage(sources, db_path=test_db)
        check("initialize_lineage creates nodes", created == 8)
        check("lineage has 8 nodes", len(database.get_lineage_nodes(test_db)) == 8)
        check("lineage has 6 edges", len(database.get_lineage_edges(test_db)) == 6)

        # idempotency
        created_again = pipeline.initialize_lineage(sources, db_path=test_db)
        check("initialize_lineage is idempotent (no duplicates)", created_again == 0)
        check("still 8 nodes after re-run", len(database.get_lineage_nodes(test_db)) == 8)
        check("still 6 edges after re-run", len(database.get_lineage_edges(test_db)) == 6)

        # --- pipeline simulation: success ---
        result = pipeline.simulate_pipeline_run(
            "customers_csv", failure_probability=0.0, db_path=test_db
        )
        check("successful run reports success", result["status"] == "success")
        check("successful run creates version v1", result["version_number"] == 1)
        version = database.get_version_by_id(result["version_id"], test_db)
        check("successful version stays active", version["status"] == "active")

        # --- pipeline simulation: forced failure ---
        result2 = pipeline.simulate_pipeline_run(
            "customers_csv", force_failure=True, db_path=test_db
        )
        check("forced run reports failure", result2["status"] == "failure")
        check("failed run creates version v2", result2["version_number"] == 2)
        failed_version = database.get_version_by_id(result2["version_id"], test_db)
        check("failed version is marked failed", failed_version["status"] == "failed")

        # --- version numbering continues per source ---
        result3 = pipeline.simulate_pipeline_run(
            "customers_csv", failure_probability=0.0, db_path=test_db
        )
        check("version numbering continues (v3)", result3["version_number"] == 3)

        other = pipeline.simulate_pipeline_run(
            "orders_api", failure_probability=0.0, db_path=test_db
        )
        check("version numbering is per source (orders v1)", other["version_number"] == 1)

        # --- lineage chains ---
        chains = pipeline.get_lineage_chains(test_db)
        check("one chain per source", len(chains) == 2)
        customers = next(c for c in chains if c["source"] == "customers_csv")
        check("customers chain has 4 nodes", len(customers["nodes"]) == 4)
        check("chain ends at warehouse node",
              customers["nodes"][-1] == "warehouse_customers_csv")

        # --- stats ---
        stats = pipeline.get_dashboard_stats(test_db)
        check("stats count 4 runs", stats["total_runs"] == 4)
        check("stats count 2 successful runs", stats["successful_runs"] == 3)  # 1+1+1
        check("stats count 1 failed run", stats["failed_runs"] == 1)
        check("stats detect failed versions", stats["failed_versions"] == 1)

        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0

    finally:
        os.unlink(test_db)


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)
