"""Tests for environment-based configuration (Phase 7 - Docker).

The container is configured entirely with environment variables, so these tests
make sure the switches really work:

  LINEAGE_DB_PATH        - where the SQLite file lives (a mounted volume)
  AUTO_ROLLBACK_ENABLED  - turn automatic rollback on or off
  HOST / PORT            - where the web server listens

Run with:  .venv\\Scripts\\python.exe test_config.py
"""

import os
import subprocess
import sys
import tempfile

import rollback

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

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


def run_python(code, extra_env=None):
    """Run a snippet in a fresh interpreter so module-level settings are re-read."""
    env = dict(os.environ)
    env.pop("LINEAGE_DB_PATH", None)
    env.pop("AUTO_ROLLBACK_ENABLED", None)
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run_tests():
    print("Running environment configuration tests...")

    # --- 1. The true/false switch parser ---------------------------------
    true_values = ["1", "true", "TRUE", "True", "yes", "YES", "on", "On"]
    false_values = ["0", "false", "FALSE", "no", "off", "banana", ""]

    for value in true_values:
        os.environ["LINEAGE_TEST_FLAG"] = value
        check(f"_env_flag({value!r}) is True", rollback._env_flag("LINEAGE_TEST_FLAG", False) is True)

    for value in false_values:
        os.environ["LINEAGE_TEST_FLAG"] = value
        check(f"_env_flag({value!r}) is False", rollback._env_flag("LINEAGE_TEST_FLAG", True) is False)

    os.environ.pop("LINEAGE_TEST_FLAG", None)
    check("_env_flag falls back to the default when unset",
          rollback._env_flag("LINEAGE_TEST_FLAG_UNSET", True) is True)
    check("auto rollback is enabled by default (no env var)",
          run_python("import rollback; print(rollback.AUTO_ROLLBACK_ENABLED)")[0] == "True")
    check("AUTO_ROLLBACK_ENABLED=false disables rollback",
          run_python("import rollback; print(rollback.AUTO_ROLLBACK_ENABLED)",
                     {"AUTO_ROLLBACK_ENABLED": "false"})[0] == "False")

    # --- 2. Database path from the environment ---------------------------
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "volume", "nested", "custom.db")
        code = "import database; print(database.DB_PATH)"
        out, err, rc = run_python(code, {"LINEAGE_DB_PATH": target})
        check("LINEAGE_DB_PATH is used as the database file", rc == 0 and out == target)
        check("database file does not exist before connecting", not os.path.exists(target))

        code = "import database; database.init_db(); print('ok')"
        out, err, rc = run_python(code, {"LINEAGE_DB_PATH": target})
        check("init_db works with a custom path", rc == 0 and out == "ok")
        check("missing parent folders are created automatically", os.path.exists(target))

    # --- 3. Defaults -----------------------------------------------------
    out, err, rc = run_python("import database; print(database.DB_PATH)")
    check("default database path is lineage.db",
          rc == 0 and out.endswith("lineage.db"))

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_tests() else 1)
