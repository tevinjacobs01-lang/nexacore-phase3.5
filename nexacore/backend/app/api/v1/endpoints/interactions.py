"""
Interaction / activity timeline endpoints (Sprint 22).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.interaction import Interaction, INTERACTION_TYPES, INTERACTION_DIRECTIONS
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.user import User
from app.schemas.interaction import InteractionCreate, InteractionOut

router = APIRouter()


@router.post("/", response_model=InteractionOut, status_code=201)
def log_interaction(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.interaction_type not in INTERACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"interaction_type must be one of {sorted(INTERACTION_TYPES)}")
    if payload.direction not in INTERACTION_DIRECTIONS:
        raise HTTPException(status_code=400, detail=f"direction must be one of {sorted(INTERACTION_DIRECTIONS)}")
    if not payload.contact_id and not payload.lead_id:
        raise HTTPException(status_code=400, detail="Provide at least one of contact_id or lead_id")
    if payload.contact_id and not db.query(Contact).filter(Contact.id == payload.contact_id).first():
        raise HTTPException(status_code=404, detail="Contact not found")
    if payload.lead_id and not db.query(Lead).filter(Lead.id == payload.lead_id).first():
        raise HTTPException(status_code=404, detail="Lead not found")

    interaction = Interaction(**payload.model_dump(), user_id=user.id)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/timeline", response_model=list[InteractionOut])
def get_timeline(
    contact_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Chronological activity timeline for a contact and/or lead."""
    if not contact_id and not lead_id:
        raise HTTPException(status_code=400, detail="Provide at least one of contact_id or lead_id")

    query = db.query(Interaction)
    if contact_id:
        query = query.filter(Interaction.contact_id == contact_id)
    if lead_id:
        query = query.filter(Interaction.lead_id == lead_id)
    return query.order_by(Interaction.occurred_at.desc()).limit(limit).all()
