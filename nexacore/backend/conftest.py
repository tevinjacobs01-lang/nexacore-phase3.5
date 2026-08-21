"""
Shared pytest fixtures for the whole test suite (Phase 3.5, Task 3).

SAFETY: tests NEVER touch the real DATABASE_URL from .env / app config.
This file hard-codes an isolated SQLite database for every test run,
regardless of what's configured for local development. If a
TEST_DATABASE_URL environment variable is set, it's used instead — but
there's an explicit guard below that refuses to run if TEST_DATABASE_URL
is ever equal to DATABASE_URL, to prevent a misconfigured environment from
accidentally wiping real data.
"""
import os
import sys
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(__file__))

from app.db.base import Base  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")

# --- Safety guard: never allow the test DB to be the real one ---
_real_database_url = os.environ.get("DATABASE_URL", "")
if _real_database_url and TEST_DATABASE_URL == _real_database_url:
    raise RuntimeError(
        "TEST_DATABASE_URL is identical to DATABASE_URL. Refusing to run "
        "tests against what looks like the real/development database. "
        "Set TEST_DATABASE_URL to a separate database (or leave it unset "
        "to use the default in-memory SQLite)."
    )


@pytest.fixture(scope="function")
def db():
    """A fresh, isolated database for every single test function — tables
    created from scratch, dropped after. Nothing persists between tests,
    and nothing ever touches a real Postgres instance unless you
    deliberately set TEST_DATABASE_URL to one you're OK with wiping."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------
# Domain fixtures — one of each Phase 1-3 entity, wired together sensibly
# ---------------------------------------------------------------------

@pytest.fixture
def test_user(db):
    from app.models.user import User
    from app.core.security import hash_password
    user = User(email="agent@example.com", hashed_password=hash_password("testpassword123"), role="agent")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    from app.models.user import User
    from app.core.security import hash_password
    admin = User(email="admin@example.com", hashed_password=hash_password("adminpassword123"), role="admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_listing(db):
    """A Property — the app's term for what Phase 2/3 sprints call a 'listing'."""
    from app.models.property import Property
    prop = Property(
        address="12 Oak Street", suburb="Roodepoort", city="Johannesburg",
        province="Gauteng", listing_type="sale", property_type="House",
        bedrooms=3, bathrooms=2, asking_price=1850000, days_on_market=45,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@pytest.fixture
def test_contact(db):
    from app.models.contact import Contact
    contact = Contact(
        name="Jane Seller", phone="+27821234567", email="jane@example.com",
        contact_type="seller", preferred_contact_method="phone",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@pytest.fixture
def test_lead(db, test_listing, test_contact):
    from app.models.lead import Lead
    lead = Lead(property_id=test_listing.id, contact_id=test_contact.id, status="new", priority="medium")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@pytest.fixture
def test_interaction(db, test_lead, test_contact, test_user):
    from app.models.interaction import Interaction
    interaction = Interaction(
        lead_id=test_lead.id, contact_id=test_contact.id, user_id=test_user.id,
        interaction_type="call", direction="outgoing", outcome="left voicemail",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@pytest.fixture
def test_note(db, test_lead, test_user):
    from app.models.note import Note
    note = Note(entity_type="lead", entity_id=test_lead.id, content="Called, no answer.", author_id=test_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@pytest.fixture
def test_task(db, test_lead, test_user):
    from app.models.task import Task
    task = Task(
        title="Follow up with Jane", assigned_user_id=test_user.id, lead_id=test_lead.id,
        due_date=date.today(), priority="high", status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def test_follow_up(db, test_lead, test_contact, test_user):
    from app.models.follow_up import FollowUp
    follow_up = FollowUp(
        lead_id=test_lead.id, contact_id=test_contact.id, follow_up_type="call",
        due_at=datetime.utcnow() + timedelta(days=1), created_by=test_user.id,
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@pytest.fixture
def test_appointment(db, test_lead, test_contact):
    from app.models.appointment import Appointment
    appt = Appointment(
        lead_id=test_lead.id, contact_id=test_contact.id,
        starts_at=datetime.utcnow() + timedelta(days=2), appointment_type="viewing",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@pytest.fixture
def test_assignment(db, test_lead, test_user):
    from app.models.assignment import Assignment
    assignment = Assignment(lead_id=test_lead.id, agent_id=test_user.id, is_current=True)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    test_lead.assigned_agent_id = test_user.id
    db.commit()
    return assignment


@pytest.fixture
def test_template(db):
    from app.models.communication_template import CommunicationTemplate
    template = CommunicationTemplate(
        name="Initial Seller Outreach", template_type="initial_seller_contact",
        subject="Regarding {{property_address}}",
        body="Hi {{contact_name}}, I'm {{agent_name}}, reaching out about {{property_address}} in {{suburb}}.",
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
