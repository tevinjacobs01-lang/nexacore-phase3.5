"""
AI Assistant endpoints. All return a clear 503 if ANTHROPIC_API_KEY isn't
configured, rather than a confusing stack trace.
"""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property
from app.models.lead_score import PropertyScoreHistory
from app.schemas.ai import AskRequest, AIResponse, PrioritizeRequest
from app.services import ai_assistant

router = APIRouter()


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # upstream API error, network issue, etc.
        raise HTTPException(status_code=502, detail=f"AI assistant error: {exc}")


@router.post("/summarize/{property_id}", response_model=AIResponse)
def summarize_property(property_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return AIResponse(answer=_wrap(ai_assistant.summarize_property, prop))


@router.post("/explain-score/{property_id}", response_model=AIResponse)
def explain_score(property_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    latest = (
        db.query(PropertyScoreHistory)
        .filter(PropertyScoreHistory.property_id == property_id)
        .order_by(PropertyScoreHistory.created_at.desc())
        .first()
    )
    breakdown = json.loads(latest.breakdown) if latest and latest.breakdown else {}
    return AIResponse(answer=_wrap(ai_assistant.explain_score, prop, breakdown))


@router.post("/prioritize", response_model=AIResponse)
def prioritize(payload: PrioritizeRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    properties = (
        db.query(Property)
        .filter(Property.contact_status.notin_(["archived", "not_interested"]))
        .order_by(Property.lead_score.desc())
        .limit(payload.limit)
        .all()
    )
    return AIResponse(answer=_wrap(ai_assistant.prioritize_listings, properties))


@router.post("/ask", response_model=AIResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    properties = db.query(Property).limit(payload.limit).all()
    return AIResponse(answer=_wrap(ai_assistant.answer_question, payload.question, properties))
