"""Data Lineage Tracker with Auto Rollback - Flask App (Phase 1)."""

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the dashboard home page."""
    return render_template("index.html")


if __name__ == "__main__":
    # Lightweight settings, suitable for a college demo on a laptop.
    app.run(debug=True, host="127.0.0.1", port=5000)
