"""
Lead stage history tests (Sprint 27).

NOT EXECUTED in this sandbox — requires SQLAlchemy Session (unavailable,
no network to install). Written and statically validated only. Exercises
the leads.py endpoint logic indirectly by replicating its stage-history
recording behavior against the model layer directly (endpoint-level
integration testing needs a running FastAPI app, which also isn't
available here — see NOT EXECUTED note in the final report).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property import Property
from app.models.lead import Lead, LEAD_PIPELINE_STAGES, resolve_stage, LEGACY_STATUS_MAP
from app.models.lead_stage_history import LeadStageHistory


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


def _record_transition(db, lead, new_status):
    """Mirrors the stage-history recording done in leads.py::update_lead."""
    if new_status != lead.status:
        db.add(LeadStageHistory(lead_id=lead.id, from_stage=lead.status, to_stage=new_status))
    lead.status = new_status
    db.commit()


def test_lead_creation_records_initial_stage_history(db, prop):
    lead = Lead(property_id=prop.id)
    db.add(lead)
    db.flush()
    db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=lead.status))
    db.commit()

    history = db.query(LeadStageHistory).filter(LeadStageHistory.lead_id == lead.id).all()
    assert len(history) == 1
    assert history[0].from_stage is None
    assert history[0].to_stage == "new"


def test_stage_transition_is_recorded(db, prop):
    lead = Lead(property_id=prop.id, status="new")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    _record_transition(db, lead, "contacted")
    _record_transition(db, lead, "qualified")

    history = (
        db.query(LeadStageHistory)
        .filter(LeadStageHistory.lead_id == lead.id)
        .order_by(LeadStageHistory.changed_at.asc())
        .all()
    )
    assert len(history) == 2
    assert history[0].from_stage == "new" and history[0].to_stage == "contacted"
    assert history[1].from_stage == "contacted" and history[1].to_stage == "qualified"
    assert lead.status == "qualified"


def test_full_pipeline_stage_list_matches_sprint_27_spec():
    assert LEAD_PIPELINE_STAGES == [
        "new", "researching", "contacted", "responded", "qualified",
        "follow_up", "appointment", "listing_opportunity", "mandate_agreement",
        "won", "lost",
    ]


def test_legacy_status_resolves_to_new_pipeline_stage():
    assert resolve_stage("converted") == "won"
    assert resolve_stage("not_interested") == "lost"
    assert resolve_stage("closed") == "lost"
    assert resolve_stage("new") == "new"  # passthrough for already-valid stages


def test_legacy_map_covers_all_removed_phase2_statuses():
    # Phase 2's stages not present in the new pipeline must all have a mapping
    old_stages = {"converted", "not_interested", "closed"}
    assert old_stages == set(LEGACY_STATUS_MAP.keys())


def test_conversion_rate_calculation_logic(db, prop):
    # Two leads reach "contacted", only one reaches "qualified"
    lead1 = Lead(property_id=prop.id, status="new")
    lead2 = Lead(property_id=prop.id, status="new")
    db.add_all([lead1, lead2])
    db.commit()
    db.refresh(lead1)
    db.refresh(lead2)

    for lead in (lead1, lead2):
        db.add(LeadStageHistory(lead_id=lead.id, from_stage="new", to_stage="contacted"))
    db.add(LeadStageHistory(lead_id=lead1.id, from_stage="contacted", to_stage="qualified"))
    db.commit()

    # Replicate the conversion-rate math from leads.py::conversion_rates
    history = db.query(LeadStageHistory).all()
    reached = {}
    for h in history:
        reached.setdefault(h.to_stage, set()).add(h.lead_id)

    contacted_count = len(reached.get("contacted", set()))
    qualified_count = len(reached.get("qualified", set()))
    rate = qualified_count / contacted_count * 100

    assert contacted_count == 2
    assert qualified_count == 1
    assert rate == 50.0
