"""Seed the database with sample data for the college demonstration.

Safe to run multiple times: it first checks whether data already exists.
"""

import database


def seed():
    database.init_db()

    existing = database.get_versions()
    if existing:
        print("Database already has sample data. Nothing to do.")
        return

    print("Seeding sample data...")

    # Sample data sources with a few versions each
    v1 = database.add_version("customers_csv", 1, "Initial customer records (100 rows)")
    v2 = database.add_version("customers_csv", 2, "Added email column")
    v3 = database.add_version("customers_csv", 3, "Removed duplicate rows")
    v4 = database.add_version("orders_api", 1, "First orders snapshot")
    v5 = database.add_version("orders_api", 2, "Fixed null order amounts")

    # Sample pipeline runs (mix of success and failure)
    database.add_pipeline_run("etl_customers", v3, "success", "Processed 1000 rows")
    database.add_pipeline_run("etl_orders", v5, "success", "Processed 500 orders")
    database.add_pipeline_run("etl_customers", v2, "failure", "Column mismatch: expected 'email'")
    database.add_pipeline_run("etl_customers", v3, "success", "Re-run completed successfully")

    print("Done! Sample data created:")
    print(f"  - {len(database.get_versions())} data versions")
    print(f"  - {len(database.get_pipeline_runs())} pipeline runs")
    print(f"  - {len(database.get_rollback_logs())} rollback logs")


if __name__ == "__main__":
    seed()
