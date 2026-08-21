"""
Contact duplicate/dedupe tests (Sprint 21).

NOT EXECUTED in this sandbox — find_existing_contact() queries the Contact
table via SQLAlchemy Session, which is unavailable here (no network to
install sqlalchemy). Written and statically validated (py_compile) only.
Run with `pytest app/tests/test_contact_dedupe.py` locally to execute.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.contact import Contact
from app.services.contact_dedupe import find_existing_contact


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_finds_existing_contact_by_normalized_phone(db):
    db.add(Contact(name="Jane Agent", phone="+27821234567", email="jane@example.com"))
    db.commit()

    # Same number, different formatting ("082..." vs "+27...")
    match = find_existing_contact(db, name="Jane A.", phone="082 123 4567", email=None)
    assert match is not None
    assert match.phone == "+27821234567"


def test_finds_existing_contact_by_normalized_email(db):
    db.add(Contact(name="Jane Agent", phone=None, email="jane@example.com"))
    db.commit()

    match = find_existing_contact(db, name=None, phone=None, email="Jane@EXAMPLE.com")
    assert match is not None
    assert match.email == "jane@example.com"


def test_phone_match_takes_priority_over_email_mismatch(db):
    db.add(Contact(name="Jane", phone="+27821234567", email="jane@example.com"))
    db.commit()

    # Different email, but same phone -> still recognized as the same contact
    match = find_existing_contact(db, name="Jane", phone="0821234567", email="different@example.com")
    assert match is not None


def test_falls_back_to_name_match_when_no_phone_or_email(db):
    db.add(Contact(name="Jane Agent", phone=None, email=None))
    db.commit()

    match = find_existing_contact(db, name="jane agent", phone=None, email=None)
    assert match is not None


def test_returns_none_when_nothing_matches(db):
    db.add(Contact(name="Jane Agent", phone="+27821234567", email="jane@example.com"))
    db.commit()

    match = find_existing_contact(db, name="Someone Else", phone="+27000000000", email="nobody@nowhere.com")
    assert match is None


def test_returns_none_on_empty_contact_table(db):
    match = find_existing_contact(db, name="Anyone", phone="+27821234567", email="anyone@example.com")
    assert match is None
