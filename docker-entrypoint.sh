#!/bin/sh
# ---------------------------------------------------------------------------
# Container entrypoint for the Data Lineage Tracker.
#
#   1. Create the tables and load the sample demo data if the database is empty.
#      (seed.py is safe to run many times - it skips data that already exists.)
#   2. Start the Flask application.
#
# `exec` makes the Python process PID 1 so `docker stop` shuts it down cleanly.
# ---------------------------------------------------------------------------
set -e

echo "Starting Data Lineage Tracker container..."
echo "Database file: ${LINEAGE_DB_PATH:-/app/data/lineage.db}"

python seed.py

exec python app.py
