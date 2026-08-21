"""
Importer unit tests using an in-memory SQLite DB (fast, no Postgres needed for
this test suite). Covers: create-on-import, dedupe-by-reference update,
dedupe-by-address+suburb fallback, and skip-on-missing-key-fields.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.services.importer import import_file

CSV_BASIC = b"""Listing Reference,Address,Suburb,City,Asking Price,Days on Market
REF-A,1 Test Street,Testville,Testcity,1000000,10
REF-B,2 Test Street,Testville,Testcity,2000000,20
"""

CSV_UPDATE = b"""Listing Reference,Address,Suburb,City,Asking Price,Days on Market
REF-A,1 Test Street,Testville,Testcity,1100000,15
"""

CSV_NO_REF_DUPLICATE = b"""Address,Suburb,City,Asking Price
1 Test Street,Testville,Testcity,1250000
"""

CSV_MISSING_KEY = b"""Bedrooms,Bathrooms
3,2
"""


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_import_creates_new_properties(db):
    log = import_file(CSV_BASIC, "listings.csv", db)
    assert log.rows_processed == 2
    assert log.rows_created == 2
    assert log.rows_updated == 0
    assert db.query(Property).count() == 2


def test_import_updates_existing_by_reference(db):
    import_file(CSV_BASIC, "listings.csv", db)
    log = import_file(CSV_UPDATE, "update.csv", db)

    assert log.rows_updated == 1
    prop = db.query(Property).filter(Property.listing_reference == "REF-A").first()
    assert float(prop.asking_price) == 1100000
    assert prop.days_on_market == 15


def test_import_dedupes_by_address_suburb_when_no_reference(db):
    import_file(CSV_BASIC, "listings.csv", db)
    log = import_file(CSV_NO_REF_DUPLICATE, "no_ref.csv", db)

    # Should match REF-A's address+suburb and update it rather than creating a dup
    assert log.rows_created == 0
    assert log.rows_updated == 1
    assert db.query(Property).count() == 2


def test_import_skips_rows_missing_key_fields(db):
    log = import_file(CSV_MISSING_KEY, "bad.csv", db)
    assert log.rows_skipped == 1
    assert log.rows_created == 0
    assert len(log.errors) > 0
