"""Data Lineage Tracker with Auto Rollback - Flask App.

Phase 1: minimal website
Phase 2: SQLite database + version history
Phase 3: lineage tracking + simulated pipeline runs (dashboard + JSON API)
"""

from flask import Flask, jsonify, render_template, request

import database
import pipeline

app = Flask(__name__)

# Make sure the tables exist before the first request.
database.init_db()


@app.route("/")
def index():
    """Dashboard home page."""
    return render_template(
        "index.html",
        stats=pipeline.get_dashboard_stats(),
        versions=database.get_versions()[:20],
        runs=database.get_pipeline_runs()[:20],
        chains=pipeline.get_lineage_chains(),
        rollbacks=database.get_rollback_logs()[:20],
        sources=database.get_source_names(),
    )


# ---------------------- JSON API ----------------------

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
    return jsonify(database.get_pipeline_runs())


@app.route("/api/lineage")
def api_lineage():
    """The lineage chain for every data source."""
    return jsonify(pipeline.get_lineage_chains())


@app.route("/api/rollbacks")
def api_rollbacks():
    """All rollback events, newest first."""
    return jsonify(database.get_rollback_logs())


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Simulate a pipeline run.

    JSON body (all optional):
        {"source_name": "customers_csv", "force_failure": false}
    """
    data = request.get_json(silent=True) or {}
    source_name = data.get("source_name") or (database.get_source_names() or ["customers_csv"])[0]
    force_failure = bool(data.get("force_failure", False))

    if source_name not in database.get_source_names():
        return jsonify({"error": f"Unknown source: {source_name}"}), 400

    result = pipeline.simulate_pipeline_run(source_name, force_failure=force_failure)
    return jsonify(result)


if __name__ == "__main__":
    # Lightweight settings, suitable for a college demo on a laptop.
    app.run(debug=True, host="127.0.0.1", port=5000)
