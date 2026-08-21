"""
Task overdue/today/upcoming logic tests (Sprint 24).

NOT EXECUTED in this sandbox — requires SQLAlchemy Session (unavailable).
Written and statically validated only.
"""
import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.task import Task, TASK_PRIORITIES, TASK_STATUSES


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed_tasks(db):
    today = date.today()
    db.add_all([
        Task(title="Overdue task", due_date=today - timedelta(days=2), status="pending"),
        Task(title="Today task", due_date=today, status="pending"),
        Task(title="Upcoming task", due_date=today + timedelta(days=3), status="pending"),
        Task(title="Completed overdue task", due_date=today - timedelta(days=5), status="completed"),
        Task(title="Cancelled today task", due_date=today, status="cancelled"),
    ])
    db.commit()


def test_overdue_query_excludes_completed_and_cancelled(db):
    _seed_tasks(db)
    today = date.today()
    overdue = (
        db.query(Task)
        .filter(Task.due_date < today, Task.status.notin_(["completed", "cancelled"]))
        .all()
    )
    assert len(overdue) == 1
    assert overdue[0].title == "Overdue task"


def test_today_query_excludes_cancelled(db):
    _seed_tasks(db)
    today = date.today()
    todays = (
        db.query(Task)
        .filter(Task.due_date == today, Task.status.notin_(["completed", "cancelled"]))
        .all()
    )
    assert len(todays) == 1
    assert todays[0].title == "Today task"


def test_upcoming_query_only_future_pending(db):
    _seed_tasks(db)
    today = date.today()
    upcoming = (
        db.query(Task)
        .filter(Task.due_date > today, Task.status.notin_(["completed", "cancelled"]))
        .all()
    )
    assert len(upcoming) == 1
    assert upcoming[0].title == "Upcoming task"


def test_task_defaults(db):
    task = Task(title="No due date task")
    db.add(task)
    db.commit()
    db.refresh(task)
    assert task.priority == "medium"
    assert task.status == "pending"
    assert task.completed_at is None


def test_task_priority_and_status_enums_are_well_formed():
    assert TASK_PRIORITIES == {"low", "medium", "high", "urgent"}
    assert TASK_STATUSES == {"pending", "in_progress", "completed", "cancelled"}


def test_completing_a_task_sets_completed_at_via_endpoint_logic(db):
    """Mirrors app/api/v1/endpoints/tasks.py::update_task's completed_at logic."""
    from datetime import datetime
    task = Task(title="Task to complete", status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    new_status = "completed"
    if new_status == "completed" and task.status != "completed":
        task.completed_at = datetime.utcnow()
    task.status = new_status
    db.commit()

    assert task.status == "completed"
    assert task.completed_at is not None
