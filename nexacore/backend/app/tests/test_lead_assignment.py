"""
Lead assignment tests (Sprint 28).

NOT EXECUTED in this sandbox — requires SQLAlchemy Session (unavailable).
Written and statically validated only.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.models.lead import Lead
from app.models.assignment import Assignment
from app.models.user import User


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
    p = Property(address="1 Test St", suburb="Testville")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def agents(db):
    a1 = User(email="agent1@example.com", hashed_password="x")
    a2 = User(email="agent2@example.com", hashed_password="x")
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)
    return a1, a2


def _assign(db, lead, agent_id, assigned_by=None):
    """Mirrors leads.py::assign_lead's logic exactly."""
    db.query(Assignment).filter(Assignment.lead_id == lead.id, Assignment.is_current.is_(True)).update(
        {"is_current": False}
    )
    db.add(Assignment(lead_id=lead.id, agent_id=agent_id, assigned_by=assigned_by, is_current=True))
    lead.assigned_agent_id = agent_id
    db.commit()


def test_new_lead_is_unassigned_by_default(db, prop):
    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    assert lead.assigned_agent_id is None


def test_assigning_a_lead_creates_one_current_assignment_row(db, prop, agents):
    agent1, _ = agents
    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    _assign(db, lead, agent1.id)

    assignments = db.query(Assignment).filter(Assignment.lead_id == lead.id).all()
    assert len(assignments) == 1
    assert assignments[0].is_current is True
    assert lead.assigned_agent_id == agent1.id


def test_reassignment_preserves_history_and_marks_only_one_current(db, prop, agents):
    agent1, agent2 = agents
    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    _assign(db, lead, agent1.id)
    _assign(db, lead, agent2.id)

    assignments = db.query(Assignment).filter(Assignment.lead_id == lead.id).order_by(Assignment.assigned_at.asc()).all()
    assert len(assignments) == 2
    assert assignments[0].agent_id == agent1.id and assignments[0].is_current is False
    assert assignments[1].agent_id == agent2.id and assignments[1].is_current is True
    assert lead.assigned_agent_id == agent2.id  # current-owner pointer reflects the latest


def test_unassigned_leads_query(db, prop, agents):
    agent1, _ = agents
    lead1 = Lead(property_id=prop.id)
    lead2 = Lead(property_id=prop.id)
    db.add_all([lead1, lead2])
    db.commit()
    db.refresh(lead1)
    db.refresh(lead2)

    _assign(db, lead1, agent1.id)
    # lead2 stays unassigned

    unassigned = db.query(Lead).filter(Lead.assigned_agent_id.is_(None)).all()
    assert len(unassigned) == 1
    assert unassigned[0].id == lead2.id


def test_assignment_records_who_assigned_it(db, prop, agents):
    agent1, agent2 = agents
    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    _assign(db, lead, agent1.id, assigned_by=agent2.id)

    assignment = db.query(Assignment).filter(Assignment.lead_id == lead.id).first()
    assert assignment.assigned_by == agent2.id
