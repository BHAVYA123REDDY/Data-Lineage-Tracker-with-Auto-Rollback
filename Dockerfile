# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Data Lineage Tracker with Auto Rollback
# Small, CPU-friendly image (fits comfortably on an 8 GB laptop).
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# --- Environment -----------------------------------------------------------
# PYTHONDONTWRITEBYTECODE: no .pyc files inside the image
# PYTHONUNBUFFERED:       log lines appear immediately in `docker logs`
# HOST=0.0.0.0:           accept connections from outside the container
# LINEAGE_DB_PATH:        keep the SQLite file on a mountable volume
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    LINEAGE_DB_PATH=/app/data/lineage.db \
    AUTO_ROLLBACK_ENABLED=true

WORKDIR /app

# --- Dependencies (own layer so it is cached) ------------------------------
# Only Flask is required; SQLite ships with Python.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# --- Application code ------------------------------------------------------
COPY . .

# --- Non-root user + writable data folder ---------------------------------
RUN mkdir -p /app/data \
 && useradd --create-home --shell /bin/bash appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# --- Health check (uses the /health endpoint from Phase 5) -----------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=4).status == 200 else 1)"

# Entrypoint seeds the demo data (only when the database is empty) then starts.
ENTRYPOINT ["sh", "docker-entrypoint.sh"]
