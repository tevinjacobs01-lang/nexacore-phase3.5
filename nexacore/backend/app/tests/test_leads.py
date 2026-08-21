"""
Lead pipeline model/service-level tests (Sprint 19). In-memory SQLite.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.models.contact import Contact
from app.models.lead import Lead, LEAD_PIPELINE_STAGES
from app.models.contact import Contact
from app.models.user import User


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def prop(db):
    p = Property(address="1 Test St", suburb="Testville")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_lead_defaults_to_new_status_and_medium_priority(db, prop):
    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    assert lead.status == "new"
    assert lead.priority == "medium"


def test_lead_property_relationship(db, prop):
    lead = Lead(property_id=prop.id, priority="high")
    db.add(lead)
    db.commit()

    fetched = db.query(Lead).filter(Lead.property_id == prop.id).first()

    assert fetched is not None
    assert fetched.priority == "high"


def test_pipeline_stages_cover_full_lifecycle():
    assert LEAD_PIPELINE_STAGES == [
        "new",
        "researching",
        "contacted",
        "responded",
        "qualified",
        "follow_up",
        "appointment",
        "listing_opportunity",
        "mandate_agreement",
        "won",
        "lost",
    ]


def test_multiple_leads_can_exist_for_different_properties(db, prop):
    p2 = Property(address="2 Test St", suburb="Testville")
    db.add(p2)
    db.commit()
    db.refresh(p2)

    db.add_all([
        Lead(property_id=prop.id),
        Lead(property_id=p2.id),
    ])
    db.commit()

    assert db.query(Lead).count() == 2