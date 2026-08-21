"""
Listing status changes + history (Sprints 14, 15), and duplicate match review
(Sprint 13). Nested under /listings to keep it distinct from the core
/properties CRUD.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property
from app.models.listing_history import ListingHistory
from app.models.duplicate_match import DuplicateMatch
from app.schemas.listing_history import ListingHistoryOut, StatusChangeRequest, VALID_LISTING_STATUSES
from app.schemas.duplicate import DuplicateMatchOut
from app.services.listing_history import record_change

router = APIRouter()


@router.get("/{property_id}/history", response_model=list[ListingHistoryOut])
def get_history(property_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return (
        db.query(ListingHistory)
        .filter(ListingHistory.property_id == property_id)
        .order_by(ListingHistory.changed_at.desc())
        .all()
    )


@router.patch("/{property_id}/status", response_model=ListingHistoryOut | None)
def change_status(
    property_id: uuid.UUID,
    payload: StatusChangeRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    if payload.status not in VALID_LISTING_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_LISTING_STATUSES)}")

    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    entry = record_change(db, prop, new_status=payload.status)
    db.commit()
    if entry:
        db.refresh(entry)
    return entry


@router.get("/duplicates", response_model=list[DuplicateMatchOut])
def list_duplicates(
    resolved: bool | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(DuplicateMatch)
    if resolved is not None:
        query = query.filter(DuplicateMatch.resolved == resolved)
    return query.order_by(DuplicateMatch.created_at.desc()).all()


@router.post("/duplicates/{match_id}/resolve", response_model=DuplicateMatchOut)
def resolve_duplicate(match_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    match = db.query(DuplicateMatch).filter(DuplicateMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Duplicate match not found")
    match.resolved = True
    db.commit()
    db.refresh(match)
    return match
