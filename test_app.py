"""Tests for the web pages, JSON API and error handling (Phase 5).

Run with:  .venv\\Scripts\\python.exe test_app.py
Uses a temporary database file so your real data is never touched.
"""

import os
import tempfile

import database

# Point the application at a temporary database BEFORE importing it.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB = _tmp.name
_tmp.close()
database.DB_PATH = TEST_DB

import pipeline  # noqa: E402
import app as app_module  # noqa: E402

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


def prepare_data():
    database.init_db()
    pipeline.initialize_lineage(["customers_csv", "orders_api"])
    database.add_version("customers_csv", 1, "Initial customer records", status="active")
    database.add_version("orders_api", 1, "First orders snapshot", status="active")
    database.add_pipeline_run("etl_customers", 1, "success", "Processed 500 rows")


def run_tests():
    try:
        prepare_data()
        app_module.app.config["TESTING"] = True
        client = app_module.app.test_client()

        print("Running web app + API tests...")

        # --- pages ---
        r = client.get("/")
        check("dashboard returns 200", r.status_code == 200)
        check("dashboard shows title", b"Data Lineage Tracker" in r.data)
        check("dashboard shows lineage", b"Data Lineage" in r.data)
        check("dashboard shows source health", b"Pipeline Status by Source" in r.data)

        r = client.get("/logs")
        check("logs page returns 200", r.status_code == 200)
        check("logs page shows activity", b"Combined Activity Log" in r.data)

        r = client.get("/health")
        check("health returns 200", r.status_code == 200)
        check("health reports ok", r.get_json()["status"] == "ok")

        # --- JSON API ---
        for path in [
            "/api/status",
            "/api/versions",
            "/api/runs",
            "/api/lineage",
            "/api/rollbacks",
            "/api/current",
            "/api/config",
            "/api/logs",
        ]:
            resp = client.get(path)
            check(f"{path} returns 200", resp.status_code == 200)
            check(f"{path} returns JSON", resp.is_json)

        r = client.get("/api/logs?limit=1")
        check("api logs honours limit", len(r.get_json()) <= 1)

        # --- error handling ---
        r = client.get("/no-such-page")
        check("unknown page returns 404", r.status_code == 404)
        check("unknown page shows friendly HTML", b"Page not found" in r.data)

        r = client.get("/api/no-such-endpoint")
        check("unknown API path returns JSON 404",
              r.status_code == 404 and r.is_json)

        r = client.get("/api/logs?limit=abc")
        check("bad limit returns 400", r.status_code == 400)
        check("bad limit returns error message", "error" in r.get_json())

        r = client.post("/api/status")
        check("wrong method on API returns 405 JSON",
              r.status_code == 405 and r.is_json)

        # --- simulate validation ---
        r = client.post("/api/simulate", data="not json", content_type="application/json")
        check("invalid JSON body returns 400", r.status_code == 400)

        r = client.post("/api/simulate", json={"source_name": "unknown_source"})
        check("unknown source returns 400", r.status_code == 400)
        check("unknown source lists valid options",
              "valid_sources" in r.get_json())

        r = client.post("/api/simulate", json={"source_name": "customers_csv", "force_failure": "yes"})
        check("non-boolean force_failure returns 400", r.status_code == 400)

        r = client.post("/api/simulate", json={"source_name": "customers_csv", "force_failure": False})
        check("valid simulate returns 200", r.status_code == 200)
        check("valid simulate reports success", r.get_json()["status"] in ("success", "failure"))

        # failure triggers rollback
        r = client.post("/api/simulate", json={"source_name": "customers_csv", "force_failure": True})
        body = r.get_json()
        check("forced failure returns 200", r.status_code == 200)
        check("forced failure rolled back", body["rolled_back"] is True)

        # --- manual rollback validation ---
        r = client.post("/api/rollback", json={})
        check("rollback without version_id returns 400", r.status_code == 400)

        r = client.post("/api/rollback", json={"version_id": 99999})
        check("rollback with unknown version returns 404", r.status_code == 404)

        version = database.get_versions()[0]
        r = client.post("/api/rollback", json={"version_id": version["id"], "reason": "test"})
        check("valid manual rollback returns 200", r.status_code == 200)
        check("manual rollback reports a status",
              r.get_json()["status"] in ("rolled_back", "no_target"))

        # rollback history is now visible in the API
        r = client.get("/api/rollbacks")
        check("rollback history has entries", len(r.get_json()) >= 1)
        check("rollback history includes source name",
              r.get_json()[0].get("source_name") == "customers_csv")

        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0

    finally:
        os.unlink(TEST_DB)


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)
