"""
One-off script to seed default lead-scoring rules and import the sample CSV,
for a fresh dev environment. Run from the backend/ directory:

    python -m scripts.seed_demo_data
"""
from app.db.session import SessionLocal
from app.db.base import Base
from app.db.session import engine
from app.services.scoring_engine import seed_default_rules
from app.services.source_manager import seed_default_sources
from app.services.importer import import_file

SAMPLE_CSV_PATH = "seed_data/sample_listings.csv"


def main():
    Base.metadata.create_all(engine)  # convenience for first run without alembic
    db = SessionLocal()
    try:
        seed_default_rules(db)
        print("Seeded default lead scoring rules.")

        seed_default_sources(db)
        print("Seeded default data sources.")

        with open(SAMPLE_CSV_PATH, "rb") as f:
            log = import_file(f.read(), "sample_listings.csv", db)
        print(
            f"Imported sample listings: {log.rows_created} created, "
            f"{log.rows_updated} updated, {log.rows_skipped} skipped."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
