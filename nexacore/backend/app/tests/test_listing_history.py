"""
Listing history tests (Sprint 14). In-memory SQLite, same pattern as
test_importer.py.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.models.listing_history import ListingHistory
from app.services.listing_history import record_change


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def prop(db):
    p = Property(address="1 Test St", suburb="Testville", asking_price=1000000, listing_status="new")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_price_change_recorded_and_applied(db, prop):
    entry = record_change(db, prop, new_price=950000)
    db.commit()
    assert entry is not None
    assert float(entry.previous_price) == 1000000
    assert float(entry.new_price) == 950000
    assert float(prop.asking_price) == 950000


def test_status_change_recorded_and_applied(db, prop):
    entry = record_change(db, prop, new_status="contacted")
    db.commit()
    assert entry.previous_status == "new"
    assert entry.new_status == "contacted"
    assert prop.listing_status == "contacted"


def test_no_change_returns_none(db, prop):
    entry = record_change(db, prop, new_price=float(prop.asking_price))
    assert entry is None
    assert db.query(ListingHistory).count() == 0


def test_multiple_field_change_in_one_call(db, prop):
    entry = record_change(db, prop, new_price=900000, new_status="contacted", new_description="Motivated seller")
    db.commit()
    assert entry.previous_price is not None
    assert entry.previous_status == "new"
    assert prop.notes == "Motivated seller"
