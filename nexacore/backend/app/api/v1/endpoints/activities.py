"""
CRM activity endpoints, nested under a property: mark contacted, interested,
not interested, add a note, schedule a follow-up, archive, and view history.
Each action both writes an Activity row and updates the Property's CRM state.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property
from app.models.activity import Activity
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityOut, ACTIVITY_TYPES

router = APIRouter()


@router.get("/{property_id}/activities", response_model=list[ActivityOut])
def list_activities(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return (
        db.query(Activity)
        .filter(Activity.property_id == property_id)
        .order_by(Activity.created_at.desc())
        .all()
    )


@router.post("/{property_id}/activities", response_model=ActivityOut, status_code=201)
def add_activity(
    property_id: uuid.UUID,
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.activity_type not in ACTIVITY_TYPES:
        raise HTTPException(status_code=400, detail=f"activity_type must be one of {sorted(ACTIVITY_TYPES)}")

    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    activity = Activity(
        property_id=property_id,
        user_id=user.id,
        activity_type=payload.activity_type,
        note=payload.note,
    )
    db.add(activity)

    # Reflect the action on the property's own CRM state
    if payload.activity_type == "contacted":
        prop.contact_status = "contacted"
        prop.last_contacted_at = datetime.utcnow()
    elif payload.activity_type == "interested":
        prop.contact_status = "interested"
    elif payload.activity_type == "not_interested":
        prop.contact_status = "not_interested"
    elif payload.activity_type == "follow_up_scheduled":
        if not payload.follow_up_date:
            raise HTTPException(status_code=400, detail="follow_up_date is required for follow_up_scheduled")
        prop.follow_up_date = payload.follow_up_date
    elif payload.activity_type == "archived":
        prop.contact_status = "archived"
    # "note" activity type only records history, no status change

    db.commit()
    db.refresh(activity)
    return activity
