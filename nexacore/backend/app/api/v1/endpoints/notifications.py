"""
Dashboard reminders: follow-ups due, new high-scoring listings, properties
updated since yesterday.
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property
from app.schemas.property import PropertyOut

router = APIRouter()


@router.get("/")
def get_notifications(
    hot_score_threshold: int = Query(70, description="Minimum score to count as a 'new high-scoring listing'"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    today = date.today()
    yesterday = datetime.utcnow() - timedelta(days=1)

    follow_ups_due = (
        db.query(Property)
        .filter(Property.follow_up_date <= today, Property.contact_status != "archived")
        .order_by(Property.follow_up_date.asc())
        .all()
    )

    new_hot_listings = (
        db.query(Property)
        .filter(Property.lead_score >= hot_score_threshold, Property.created_at >= yesterday)
        .order_by(Property.lead_score.desc())
        .all()
    )

    updated_since_yesterday = (
        db.query(Property)
        .filter(Property.last_updated >= yesterday)
        .order_by(Property.last_updated.desc())
        .all()
    )

    return {
        "follow_ups_due": [PropertyOut.model_validate(p) for p in follow_ups_due],
        "new_hot_listings": [PropertyOut.model_validate(p) for p in new_hot_listings],
        "updated_since_yesterday": [PropertyOut.model_validate(p) for p in updated_since_yesterday],
    }
