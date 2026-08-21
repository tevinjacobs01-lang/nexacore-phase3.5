"""
Admin endpoints for viewing/editing lead scoring rules, plus manual recompute.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin, get_current_user
from app.db.session import get_db
from app.models.lead_score import LeadScoreRule
from app.models.property import Property
from app.schemas.scoring import LeadScoreRuleOut, LeadScoreRuleCreate, LeadScoreRuleUpdate
from app.services.scoring_engine import recompute_score, recompute_all_scores

router = APIRouter()


@router.get("/rules", response_model=list[LeadScoreRuleOut])
def list_rules(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return db.query(LeadScoreRule).order_by(LeadScoreRule.name).all()


@router.post("/rules", response_model=LeadScoreRuleOut, status_code=201)
def create_rule(payload: LeadScoreRuleCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if db.query(LeadScoreRule).filter(LeadScoreRule.rule_key == payload.rule_key).first():
        raise HTTPException(status_code=400, detail="rule_key already exists")
    rule = LeadScoreRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=LeadScoreRuleOut)
def update_rule(
    rule_id: uuid.UUID,
    payload: LeadScoreRuleUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    rule = db.query(LeadScoreRule).filter(LeadScoreRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/recompute")
def recompute_all(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    count = recompute_all_scores(db)
    return {"recomputed": count}


@router.post("/recompute/{property_id}")
def recompute_one(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    recompute_score(db, prop)
    db.commit()
    db.refresh(prop)
    return {"property_id": prop.id, "lead_score": prop.lead_score}
