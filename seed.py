"""Seed the database with sample data for the college demonstration.

Safe to run multiple times: it checks what already exists before inserting.
"""

import database
import pipeline

SOURCES = ["customers_csv", "orders_api"]


def seed():
    database.init_db()

    # --- 1. Sample data versions and pipeline runs (Phase 2) ---
    if database.get_versions():
        print("Sample versions already exist. Skipping version seed.")
    else:
        print("Seeding sample versions and pipeline runs...")

        v1 = database.add_version("customers_csv", 1, "Initial customer records (100 rows)")
        v2 = database.add_version("customers_csv", 2, "Added email column")
        v3 = database.add_version("customers_csv", 3, "Removed duplicate rows")
        database.add_version("orders_api", 1, "First orders snapshot")
        v5 = database.add_version("orders_api", 2, "Fixed null order amounts")

        database.add_pipeline_run("etl_customers", v3, "success", "Processed 1000 rows")
        database.add_pipeline_run("etl_orders", v5, "success", "Processed 500 orders")
        database.add_pipeline_run("etl_customers", v2, "failure", "Column mismatch: expected 'email'")
        database.add_pipeline_run("etl_customers", v3, "success", "Re-run completed successfully")

    # --- 2. Lineage graph (Phase 3) ---
    created = pipeline.initialize_lineage(SOURCES)
    if created:
        print(f"Created {created} new lineage nodes.")
    else:
        print("Lineage graph already exists. Nothing to do.")

    print("\nDatabase is ready:")
    print(f"  - {len(database.get_versions())} data versions")
    print(f"  - {len(database.get_pipeline_runs())} pipeline runs")
    print(f"  - {len(database.get_lineage_nodes())} lineage nodes")
    print(f"  - {len(database.get_lineage_edges())} lineage edges")
    print(f"  - {len(database.get_rollback_logs())} rollback logs")


if __name__ == "__main__":
    seed()
