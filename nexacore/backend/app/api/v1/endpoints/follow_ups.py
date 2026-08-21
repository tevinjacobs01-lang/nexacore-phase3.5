"""
Follow-up engine endpoints (Sprint 25). "Overdue" is always derived
(pending + due_at in the past) rather than a stored status, so it can never
drift out of sync with the actual due date.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.follow_up import FollowUp, FOLLOW_UP_TYPES, FOLLOW_UP_STATUSES
from app.models.lead import Lead
from app.models.contact import Contact
from app.models.user import User
from app.schemas.follow_up import FollowUpCreate, FollowUpUpdate, FollowUpOut

router = APIRouter()


@router.post("/", response_model=FollowUpOut, status_code=201)
def create_follow_up(payload: FollowUpCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.follow_up_type not in FOLLOW_UP_TYPES:
        raise HTTPException(status_code=400, detail=f"follow_up_type must be one of {sorted(FOLLOW_UP_TYPES)}")
    if not payload.lead_id and not payload.contact_id:
        raise HTTPException(status_code=400, detail="Provide at least one of lead_id or contact_id")
    if payload.lead_id and not db.query(Lead).filter(Lead.id == payload.lead_id).first():
        raise HTTPException(status_code=404, detail="Lead not found")
    if payload.contact_id and not db.query(Contact).filter(Contact.id == payload.contact_id).first():
        raise HTTPException(status_code=404, detail="Contact not found")

    follow_up = FollowUp(**payload.model_dump(), created_by=user.id)
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@router.get("/dashboard")
def follow_up_dashboard(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Due today / overdue / upcoming / completed — the "never silently
    disappear" view."""
    now = datetime.utcnow()
    today_end = datetime.combine(now.date(), datetime.max.time())
    today_start = datetime.combine(now.date(), datetime.min.time())

    due_today = (
        db.query(FollowUp)
        .filter(FollowUp.status == "pending", FollowUp.due_at >= today_start, FollowUp.due_at <= today_end)
        .order_by(FollowUp.due_at.asc())
        .all()
    )
    overdue = (
        db.query(FollowUp)
        .filter(FollowUp.status == "pending", FollowUp.due_at < today_start)
        .order_by(FollowUp.due_at.asc())
        .all()
    )
    upcoming = (
        db.query(FollowUp)
        .filter(FollowUp.status == "pending", FollowUp.due_at > today_end)
        .order_by(FollowUp.due_at.asc())
        .all()
    )
    completed = (
        db.query(FollowUp)
        .filter(FollowUp.status == "completed")
        .order_by(FollowUp.completed_at.desc())
        .limit(20)
        .all()
    )

    def out(items):
        return [FollowUpOut.model_validate(i) for i in items]

    return {
        "due_today": out(due_today),
        "overdue": out(overdue),
        "upcoming": out(upcoming),
        "completed": out(completed),
    }


@router.patch("/{follow_up_id}", response_model=FollowUpOut)
def update_follow_up(
    follow_up_id: uuid.UUID,
    payload: FollowUpUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    follow_up = db.query(FollowUp).filter(FollowUp.id == follow_up_id).first()
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in FOLLOW_UP_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(FOLLOW_UP_STATUSES)}")

    if updates.get("status") == "completed" and follow_up.status != "completed":
        follow_up.completed_at = datetime.utcnow()

    for field, value in updates.items():
        setattr(follow_up, field, value)

    db.commit()
    db.refresh(follow_up)
    return follow_up
