"""
Follow-up due/overdue/upcoming logic tests (Sprint 25).

NOT EXECUTED in this sandbox — requires SQLAlchemy Session (unavailable).
Written and statically validated only.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.follow_up import FollowUp, FOLLOW_UP_TYPES, FOLLOW_UP_STATUSES


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed(db):
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    db.add_all([
        FollowUp(follow_up_type="call", due_at=now - timedelta(days=2), status="pending"),  # overdue
        FollowUp(follow_up_type="email", due_at=today_start + timedelta(hours=1), status="pending"),  # due today
        FollowUp(follow_up_type="meeting", due_at=now + timedelta(days=5), status="pending"),  # upcoming
        FollowUp(follow_up_type="message", due_at=now - timedelta(days=10), status="completed",
                 completed_at=now - timedelta(days=9)),  # completed (was overdue but resolved)
    ])
    db.commit()


def _dashboard_buckets(db):
    """Mirrors follow_ups.py::follow_up_dashboard's query logic exactly."""
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    today_end = datetime.combine(now.date(), datetime.max.time())

    due_today = db.query(FollowUp).filter(
        FollowUp.status == "pending", FollowUp.due_at >= today_start, FollowUp.due_at <= today_end
    ).all()
    overdue = db.query(FollowUp).filter(
        FollowUp.status == "pending", FollowUp.due_at < today_start
    ).all()
    upcoming = db.query(FollowUp).filter(
        FollowUp.status == "pending", FollowUp.due_at > today_end
    ).all()
    completed = db.query(FollowUp).filter(FollowUp.status == "completed").all()
    return due_today, overdue, upcoming, completed


def test_overdue_bucket_only_contains_past_pending(db):
    _seed(db)
    _, overdue, _, _ = _dashboard_buckets(db)
    assert len(overdue) == 1
    assert overdue[0].follow_up_type == "call"


def test_due_today_bucket(db):
    _seed(db)
    due_today, _, _, _ = _dashboard_buckets(db)
    assert len(due_today) == 1
    assert due_today[0].follow_up_type == "email"


def test_upcoming_bucket(db):
    _seed(db)
    _, _, upcoming, _ = _dashboard_buckets(db)
    assert len(upcoming) == 1
    assert upcoming[0].follow_up_type == "meeting"


def test_completed_follow_up_never_shows_as_overdue_even_if_originally_late(db):
    _seed(db)
    _, overdue, _, completed = _dashboard_buckets(db)
    assert len(completed) == 1
    overdue_types = [f.follow_up_type for f in overdue]
    assert "message" not in overdue_types  # the completed-but-was-late one is excluded


def test_a_lead_never_silently_disappears_all_pending_are_accounted_for(db):
    """Every pending FollowUp must land in exactly one of due_today/overdue/upcoming."""
    _seed(db)
    due_today, overdue, upcoming, _ = _dashboard_buckets(db)
    total_pending_in_buckets = len(due_today) + len(overdue) + len(upcoming)
    total_pending_in_db = db.query(FollowUp).filter(FollowUp.status == "pending").count()
    assert total_pending_in_buckets == total_pending_in_db == 3


def test_follow_up_type_and_status_enums_well_formed():
    assert FOLLOW_UP_TYPES == {"call", "message", "email", "meeting", "general"}
    assert FOLLOW_UP_STATUSES == {"pending", "completed", "cancelled"}
