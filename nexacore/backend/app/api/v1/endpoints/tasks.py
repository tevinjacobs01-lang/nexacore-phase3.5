"""
Task management endpoints (Sprint 24).
"""
import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task import Task, TASK_PRIORITIES, TASK_STATUSES
from app.models.lead import Lead
from app.models.contact import Contact
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut

router = APIRouter()


@router.get("/", response_model=list[TaskOut])
def list_tasks(
    status: str | None = None,
    assigned_user_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if assigned_user_id:
        query = query.filter(Task.assigned_user_id == assigned_user_id)
    if lead_id:
        query = query.filter(Task.lead_id == lead_id)
    return query.order_by(Task.due_date.asc().nullslast()).offset(skip).limit(limit).all()


@router.get("/today", response_model=list[TaskOut])
def todays_tasks(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(Task)
        .filter(Task.due_date == date.today(), Task.status.notin_(["completed", "cancelled"]))
        .order_by(Task.priority.desc())
        .all()
    )


@router.get("/overdue", response_model=list[TaskOut])
def overdue_tasks(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(Task)
        .filter(Task.due_date < date.today(), Task.status.notin_(["completed", "cancelled"]))
        .order_by(Task.due_date.asc())
        .all()
    )


@router.get("/upcoming", response_model=list[TaskOut])
def upcoming_tasks(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(Task)
        .filter(Task.due_date > date.today(), Task.status.notin_(["completed", "cancelled"]))
        .order_by(Task.due_date.asc())
        .all()
    )


@router.post("/", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if payload.priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of {sorted(TASK_PRIORITIES)}")
    if payload.lead_id and not db.query(Lead).filter(Lead.id == payload.lead_id).first():
        raise HTTPException(status_code=404, detail="Lead not found")
    if payload.contact_id and not db.query(Contact).filter(Contact.id == payload.contact_id).first():
        raise HTTPException(status_code=404, detail="Contact not found")
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, payload: TaskUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)
    if "priority" in updates and updates["priority"] not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of {sorted(TASK_PRIORITIES)}")
    if "status" in updates and updates["status"] not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(TASK_STATUSES)}")

    if updates.get("status") == "completed" and task.status != "completed":
        task.completed_at = datetime.utcnow()

    for field, value in updates.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task
