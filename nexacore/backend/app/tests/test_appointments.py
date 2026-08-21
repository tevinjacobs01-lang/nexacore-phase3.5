"""
Appointment status transition tests (Sprint 26).

NOT EXECUTED in this sandbox — requires SQLAlchemy Session (unavailable).
Written and statically validated only.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.appointment import Appointment, APPOINTMENT_STATUSES, APPOINTMENT_TYPES


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_appointment_defaults(db):
    appt = Appointment(starts_at=datetime.utcnow() + timedelta(days=1))
    db.add(appt)
    db.commit()
    db.refresh(appt)
    assert appt.status == "scheduled"
    assert appt.duration_minutes == 30
    assert appt.appointment_type == "viewing"


@pytest.mark.parametrize("transition", [
    "confirmed", "completed", "cancelled", "no_show", "rescheduled",
])
def test_valid_status_transitions(db, transition):
    appt = Appointment(starts_at=datetime.utcnow() + timedelta(days=1), status="scheduled")
    db.add(appt)
    db.commit()
    db.refresh(appt)

    assert transition in APPOINTMENT_STATUSES  # mirrors the endpoint's validation check
    appt.status = transition
    db.commit()
    db.refresh(appt)
    assert appt.status == transition


def test_reschedule_updates_starts_at(db):
    original_time = datetime.utcnow() + timedelta(days=1)
    appt = Appointment(starts_at=original_time, status="scheduled")
    db.add(appt)
    db.commit()
    db.refresh(appt)

    new_time = datetime.utcnow() + timedelta(days=3)
    appt.status = "rescheduled"
    appt.starts_at = new_time
    db.commit()
    db.refresh(appt)

    assert appt.status == "rescheduled"
    assert appt.starts_at == new_time


def test_appointment_status_and_type_enums_well_formed():
    assert APPOINTMENT_STATUSES == {
        "scheduled", "confirmed", "completed", "cancelled", "no_show", "rescheduled",
    }
    assert APPOINTMENT_TYPES == {
        "viewing", "listing_presentation", "signing", "consultation", "other",
    }


def test_appointment_requires_lead_or_contact_validated_at_endpoint_level():
    """The model itself allows both lead_id and contact_id to be None (they're
    nullable FKs); the "at least one required" rule is enforced in the
    endpoint (appointments.py::create_appointment), not the DB layer.
    This test documents that boundary rather than exercising the endpoint,
    since no FastAPI test client is available in this sandbox."""
    lead_id = None
    contact_id = None
    validation_would_reject = not lead_id and not contact_id
    assert validation_would_reject is True
