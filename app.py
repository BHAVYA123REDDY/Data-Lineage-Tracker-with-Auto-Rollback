"""Data Lineage Tracker with Auto Rollback - Flask App.

Phase 1: minimal website
Phase 2: SQLite database + version history
Phase 3: lineage tracking + simulated pipeline runs (dashboard + JSON API)
Phase 4: automatic rollback to the last successful version
Phase 5: dashboard/log pages, health check, and friendly error handling
"""

import logging
import os

from flask import Flask, jsonify, render_template, request

import database
import pipeline
import rollback

# ---------------------------------------------------------------------------
# Logging: everything is written to app.log as well as the console.
# ---------------------------------------------------------------------------
LOG_PATH = os.environ.get("LINEAGE_LOG_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "app.log"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("lineage-tracker")

app = Flask(__name__)

# Make sure the tables exist before the first request.
database.init_db()


def wants_json():
    """True when the request is an API call (so we can return JSON errors)."""
    return request.path.startswith("/api/")


def parse_json_body():
    """Read a JSON object from the request.

    Returns (data, error_response). An empty body is allowed and becomes {},
    but a malformed body or a non-object body is rejected with a clear message.
    """
    raw = request.get_data(as_text=True) or ""
    data = request.get_json(silent=True)

    if data is None:
        if raw.strip():
            return None, (jsonify({"error": "Request body must be valid JSON"}), 400)
        return {}, None

    if not isinstance(data, dict):
        return None, (jsonify({"error": "Request body must be a JSON object"}), 400)

    return data, None


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Dashboard home page."""
    sources = database.get_source_names()
    return render_template(
        "index.html",
        stats=pipeline.get_dashboard_stats(),
        source_status=pipeline.get_source_status(),
        versions=database.get_versions()[:20],
        runs=database.get_pipeline_runs_detailed(limit=20),
        chains=pipeline.get_lineage_chains(),
        rollbacks=database.get_rollback_logs_detailed(limit=20),
        activity=pipeline.get_activity_log(limit=10),
        sources=sources,
        current={s: rollback.get_current_version(s) for s in sources},
        auto_rollback=rollback.AUTO_ROLLBACK_ENABLED,
    )


@app.route("/logs")
def logs_page():
    """Full activity log: pipeline runs and rollback events together."""
    return render_template(
        "logs.html",
        activity=pipeline.get_activity_log(limit=200),
        runs=database.get_pipeline_runs_detailed(limit=200),
        rollbacks=database.get_rollback_logs_detailed(limit=200),
        stats=pipeline.get_dashboard_stats(),
    )


@app.route("/health")
def health():
    """Simple health check used by Docker, Jenkins and Kubernetes later."""
    try:
        stats = pipeline.get_dashboard_stats()
        return jsonify({"status": "ok", "database": "reachable", "stats": stats}), 200
    except Exception as exc:  # pragma: no cover - only on real failures
        logger.exception("Health check failed")
        return jsonify({"status": "error", "database": "unreachable", "error": str(exc)}), 503


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    """Summary counts, handy for CI checks and the dashboard."""
    return jsonify(pipeline.get_dashboard_stats())


@app.route("/api/versions")
def api_versions():
    """All stored data versions, newest first."""
    return jsonify(database.get_versions())


@app.route("/api/runs")
def api_runs():
    """All pipeline runs, newest first."""
    return jsonify(database.get_pipeline_runs_detailed())


@app.route("/api/lineage")
def api_lineage():
    """The lineage chain for every data source."""
    return jsonify(pipeline.get_lineage_chains())


@app.route("/api/rollbacks")
def api_rollbacks():
    """All rollback events, newest first."""
    return jsonify(database.get_rollback_logs_detailed())


@app.route("/api/current")
def api_current():
    """The version currently in use for every data source."""
    return jsonify(
        [
            {"source_name": source, "current_version": rollback.get_current_version(source)}
            for source in database.get_source_names()
        ]
    )


@app.route("/api/logs")
def api_logs():
    """Combined activity log as JSON."""
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "limit must be a whole number"}), 400
    limit = max(1, min(limit, 500))
    return jsonify(pipeline.get_activity_log(limit=limit))


@app.route("/api/config")
def api_config():
    """Configuration used by the demo."""
    return jsonify(
        {
            "auto_rollback_enabled": rollback.AUTO_ROLLBACK_ENABLED,
            "failure_probability": pipeline.DEFAULT_FAILURE_PROBABILITY,
        }
    )


@app.route("/api/rollback", methods=["POST"])
def api_rollback():
    """Manually roll back a failed version (useful for the demo).

    JSON body:
        {"version_id": 7, "run_id": 6, "reason": "manual demo rollback"}
    """
    data, error = parse_json_body()
    if error:
        return error

    version_id = data.get("version_id")
    if not isinstance(version_id, int):
        return jsonify({"error": "version_id must be a whole number"}), 400

    version = database.get_version_by_id(version_id)
    if version is None:
        return jsonify({"error": f"Version {version_id} not found"}), 404

    result = rollback.perform_rollback(
        version["source_name"],
        failed_run_id=data.get("run_id"),
        failed_version_id=version_id,
        reason=data.get("reason", "Manual rollback requested"),
    )
    logger.info("Manual rollback requested for version %s: %s", version_id, result["status"])
    return jsonify(result)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Simulate a pipeline run.

    JSON body (all optional):
        {"source_name": "customers_csv", "force_failure": false}
    """
    data, error = parse_json_body()
    if error:
        return error

    sources = database.get_source_names()
    if not sources:
        return jsonify({"error": "No data sources configured. Run seed.py first."}), 409

    source_name = data.get("source_name", sources[0])
    if not isinstance(source_name, str):
        return jsonify({"error": "source_name must be text"}), 400
    if source_name not in sources:
        return jsonify(
            {"error": f"Unknown source: {source_name}", "valid_sources": sources}
        ), 400

    force_failure = data.get("force_failure", False)
    if not isinstance(force_failure, bool):
        return jsonify({"error": "force_failure must be true or false"}), 400

    result = pipeline.simulate_pipeline_run(source_name, force_failure=force_failure)
    logger.info(
        "Simulated run for %s: %s (rolled_back=%s)",
        source_name,
        result["status"],
        result["rolled_back"],
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    if wants_json():
        return jsonify({"error": "Not found", "path": request.path}), 404
    return render_template("error.html", code=404, message="Page not found"), 404


@app.errorhandler(405)
def method_not_allowed(error):
    if wants_json():
        return jsonify({"error": "Method not allowed", "path": request.path}), 405
    return render_template("error.html", code=405, message="Method not allowed"), 405


@app.errorhandler(500)
def server_error(error):
    logger.exception("Unhandled server error")
    if wants_json():
        return jsonify({"error": "Internal server error"}), 500
    return render_template("error.html", code=500, message="Something went wrong"), 500


if __name__ == "__main__":
    # Lightweight settings, suitable for a college demo on a laptop.
    # In a container HOST is set to 0.0.0.0 so the port can be published.
    # Set FLASK_DEBUG=1 to enable auto-reload while editing.
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    logger.info("Starting Data Lineage Tracker on http://%s:%s", host, port)
    app.run(debug=debug_mode, host=host, port=port)
