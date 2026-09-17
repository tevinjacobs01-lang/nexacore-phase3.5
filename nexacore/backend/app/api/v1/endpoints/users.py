import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.models.discovery_event import DiscoveryEvent
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut, UserApprovalRequest

router = APIRouter()


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Return active users that can be assigned to leads.
    """
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.approval_status == "approved")
        .order_by(User.full_name.asc(), User.email.asc())
        .all()
    )


@router.get("/pending", response_model=list[UserOut])
def list_pending_users(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return db.query(User).filter(User.approval_status == "pending").order_by(User.created_at.asc()).all()


@router.patch("/{user_id}/approve", response_model=UserOut)
def approve_user(user_id: uuid.UUID, payload: UserApprovalRequest, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if payload.role not in {"admin", "agent", "user"}:
        raise HTTPException(status_code=400, detail="New users may be approved as admin, agent, or user")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.email_verified:
        raise HTTPException(status_code=409, detail="User must verify email before approval")
    user.role = payload.role
    user.approval_status = "approved"
    user.is_active = True
    user.approved_by = admin.id
    user.approved_at = datetime.now(timezone.utc)
    user.rejection_reason = None
    db.add(DiscoveryEvent(user_id=admin.id, event_type="user_approved", payload=f'{{"user_id":"{user.id}","role":"{user.role}"}}'))
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/reject", response_model=UserOut)
def reject_user(user_id: uuid.UUID, payload: UserApprovalRequest, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.approval_status = "rejected"
    user.is_active = False
    user.rejection_reason = payload.reason or "Access rejected by owner/admin"
    db.add(DiscoveryEvent(user_id=admin.id, event_type="user_rejected", payload=f'{{"user_id":"{user.id}"}}'))
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/disable", response_model=UserOut)
def disable_user(user_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = False
    db.add(DiscoveryEvent(user_id=admin.id, event_type="user_disabled", payload=f'{{"user_id":"{user.id}"}}'))
    db.commit()
    db.refresh(user)
    return user


def _legacy_active_users(
    db: Session,
    _user=Depends(require_admin),
):
    return (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.full_name.asc(), User.email.asc())
        .all()
    )