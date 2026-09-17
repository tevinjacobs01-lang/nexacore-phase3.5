import ast
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.discovery_event import DiscoveryEvent
from app.models.discovery_opportunity import DiscoveryOpportunity
from app.models.duplicate_match import DuplicateMatch
from app.models.listing_observation import ListingObservation
from app.models.property import Property
from app.models.user import User
from app.models.contact import Contact
from app.models.contact_property import ContactProperty
from app.models.lead import Lead
from app.models.lead_stage_history import LeadStageHistory
from app.models.lead_score import PropertyScoreHistory
from app.schemas.discovery import (
    DiscoveryEventOut,
    DiscoveryOpportunityListOut,
    DiscoveryOpportunityOut,
    DiscoveryReviewRequest,
    DiscoveryPromotionOut,
    DiscoveryPromotionRequest,
    DiscoveryContactUpdate,
)
from app.models.saved_search import SavedSearch
from app.schemas.saved_search import SavedSearchCreate, SavedSearchOut, SavedSearchUpdate
from app.services.discovery_search import match_saved_search
from app.services.contact_dedupe import find_existing_contact
from app.services.normalization import normalize_email, normalize_phone
from app.services.opportunity_intelligence import calculate_opportunity_intelligence
from app.services.intelligence_action_planner import plan_intelligence_action
from app.models.task import Task

router = APIRouter()

CLASSIFICATIONS = {"seller", "landlord", "unknown"}
QUALIFICATION_STATUSES = {"unreviewed", "qualified", "not_qualified", "review_required"}


def promotion_state(db: Session, opportunity: DiscoveryOpportunity) -> dict:
    """Describe CRM promotion using existing opportunity and lead records."""
    lead = None
    if opportunity.classification in {"seller", "landlord"}:
        lead = db.query(Lead).filter(
            Lead.property_id == opportunity.property_id,
            Lead.lead_type == opportunity.classification,
        ).first()
    if lead is not None:
        return {
            "crm_status": "promoted",
            "promotion_eligible": False,
            "promotion_block_reason": None,
            "lead_id": lead.id,
            "lead_status": lead.status,
        }
    if opportunity.qualification_status != "qualified":
        reason = "Opportunity requires qualification."
    elif opportunity.classification not in {"seller", "landlord"}:
        reason = "Opportunity is not eligible for CRM promotion."
    elif opportunity.property is None:
        reason = "Property information is incomplete."
    elif opportunity.latest_observation is None:
        reason = "Listing observation is required before CRM promotion."
    else:
        observation = opportunity.latest_observation
        if not (observation.contact_phone or observation.contact_email):
            reason = "Contact information is required."
        else:
            return {
                "crm_status": "promotion_eligible",
                "promotion_eligible": True,
                "promotion_block_reason": None,
                "lead_id": None,
                "lead_status": None,
            }
    return {
        "crm_status": "not_promoted",
        "promotion_eligible": False,
        "promotion_block_reason": reason,
        "lead_id": None,
        "lead_status": None,
    }


def _property_data(prop: Property) -> dict:
    return {
        "id": prop.id,
        "address": prop.address,
        "suburb": prop.suburb,
        "city": prop.city,
        "province": prop.province,
        "property_type": prop.property_type,
        "listing_type": prop.listing_type,
        "seller_type": prop.seller_type,
        "is_owner_listed": prop.is_owner_listed,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "garages": prop.garages,
        "floor_size_sqm": prop.floor_size_sqm,
        "stand_size_sqm": prop.stand_size_sqm,
        "asking_price": prop.asking_price,
        "monthly_rental": prop.monthly_rental,
        "listing_url": prop.listing_url,
        "listing_status": prop.listing_status,
        "lead_score": prop.lead_score,
        "created_at": prop.created_at,
    }


def _observation_data(observation: ListingObservation | None) -> dict | None:
    if observation is None:
        return None
    raw_payload = {}
    if observation.raw_payload:
        try:
            raw_payload = json.loads(observation.raw_payload)
        except (TypeError, ValueError):
            try:
                raw_payload = ast.literal_eval(observation.raw_payload)
            except (TypeError, ValueError, SyntaxError):
                raw_payload = {}
    portal_methods = raw_payload.get("portal_contact_methods", [])
    has_direct_contact = bool(observation.contact_phone or observation.contact_email)
    return {
        "id": observation.id,
        "source_id": observation.source_id,
        "source_listing_id": observation.source_listing_id,
        "canonical_url": observation.canonical_url,
        "source_type": observation.source_type,
        "discovery_method": observation.discovery_method,
        "source_confidence": observation.source_confidence,
        "contact_name": observation.contact_name,
        "contact_phone": observation.contact_phone,
        "contact_email": observation.contact_email,
        "contact_company": observation.contact_company,
        "contact_agency": observation.contact_agency,
        "contact_confidence": observation.contact_confidence,
        "contact_availability": "direct" if has_direct_contact else "portal_mediated" if portal_methods else "unavailable",
        "portal_contact_methods": portal_methods,
        "lifecycle_status": observation.lifecycle_status,
        "first_seen_at": observation.first_seen_at,
        "last_seen_at": observation.last_seen_at,
        "observed_at": observation.observed_at,
        "source_updated_at": observation.source_updated_at,
        "media": [],
    }


def _serialize(db: Session, opportunity: DiscoveryOpportunity) -> DiscoveryOpportunityOut:
    intelligence = calculate_opportunity_intelligence(db, opportunity)
    observation = opportunity.latest_observation
    duplicate = db.query(DuplicateMatch).filter(
        or_(
            DuplicateMatch.property_id == opportunity.property_id,
            DuplicateMatch.matched_property_id == opportunity.property_id,
        ),
        DuplicateMatch.resolved.is_(False),
    ).first()
    duplicate_data = None
    if duplicate:
        duplicate_data = {"match_type": duplicate.match_type, "match_reason": duplicate.match_reason}
    score_history = db.query(PropertyScoreHistory).filter(
        PropertyScoreHistory.property_id == opportunity.property_id,
    ).order_by(PropertyScoreHistory.created_at.desc()).first()
    breakdown = json.loads(score_history.breakdown) if score_history and score_history.breakdown else {}
    score = intelligence.score
    reasons = intelligence.reasons or (json.loads(opportunity.intelligence_reasons) if opportunity.intelligence_reasons else [key.replace("_", " ") for key in breakdown])
    score_band = "HOT" if score >= 80 else "HIGH" if score >= 60 else "WATCH" if score >= 35 else "LOW"
    return DiscoveryOpportunityOut(
        id=opportunity.id,
        property_id=opportunity.property_id,
        classification=opportunity.classification,
        qualification_status=opportunity.qualification_status,
        qualification_reason=opportunity.qualification_reason,
        discovery_score=opportunity.discovery_score,
        opportunity_score=intelligence.score,
        signal_score=intelligence.signal_score,
        data_confidence=intelligence.confidence,
        intelligence_reasons=reasons,
        recommended_action=intelligence.next_action,
        historical_signals=intelligence.historical_signals,
        score_band=score_band,
        score_reasons=reasons,
        reviewed_by=opportunity.reviewed_by,
        reviewed_at=opportunity.reviewed_at,
        **promotion_state(db, opportunity),
        property=_property_data(opportunity.property),
        observation=_observation_data(observation),
        duplicate=duplicate_data,
    )


@router.get("/opportunities", response_model=DiscoveryOpportunityListOut)
def list_opportunities(
    classification: str | None = None,
    qualification_status: str | None = None,
    property_type: str | None = None,
    suburb: str | None = None,
    source_id: uuid.UUID | None = None,
    listing_status: str | None = None,
    listed_by: str | None = Query(None, pattern="^(owner|agent_agency|unknown)$"),
    listing_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_score: int | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(DiscoveryOpportunity).join(Property).outerjoin(
        ListingObservation,
        DiscoveryOpportunity.latest_observation_id == ListingObservation.id,
    )
    if classification:
        query = query.filter(DiscoveryOpportunity.classification == classification)
    if qualification_status:
        query = query.filter(DiscoveryOpportunity.qualification_status == qualification_status)
    if property_type:
        query = query.filter(Property.property_type.ilike(f"%{property_type}%"))
    if suburb:
        query = query.filter(Property.suburb.ilike(f"%{suburb}%"))
    if source_id:
        query = query.filter(ListingObservation.source_id == source_id)
    if listing_status:
        query = query.filter(Property.listing_status == listing_status)
    if listed_by == "owner":
        query = query.filter(
            DiscoveryOpportunity.classification.in_(["seller", "landlord"]),
            or_(Property.seller_type == "owner", Property.is_owner_listed.is_(True)),
        )
    if listed_by == "agent_agency":
        query = query.filter(Property.seller_type.in_(["agent", "agency"]))
    if listed_by == "unknown":
        query = query.filter(
            or_(Property.seller_type.is_(None), Property.seller_type == "unknown"),
            or_(Property.is_owner_listed.is_(None), Property.is_owner_listed.is_(False)),
        )
    if listing_type:
        query = query.filter(Property.listing_type == listing_type)
    if min_price is not None:
        query = query.filter(func.coalesce(Property.asking_price, Property.monthly_rental) >= min_price)
    if max_price is not None:
        query = query.filter(func.coalesce(Property.asking_price, Property.monthly_rental) <= max_price)
    if min_score is not None:
        query = query.filter(DiscoveryOpportunity.opportunity_score >= min_score)
    if q:
        term = f"%{q}%"
        query = query.filter(or_(
            Property.address.ilike(term), Property.suburb.ilike(term), Property.city.ilike(term),
            Property.province.ilike(term), Property.property_type.ilike(term),
            Property.listing_source.ilike(term), ListingObservation.source_listing_id.ilike(term),
            ListingObservation.contact_name.ilike(term), DiscoveryOpportunity.classification.ilike(term),
        ))

    total = query.count()
    opportunities = query.order_by(DiscoveryOpportunity.opportunity_score.desc(), DiscoveryOpportunity.updated_at.desc()).offset(skip).limit(limit).all()
    metrics_query = db.query(DiscoveryOpportunity.classification, DiscoveryOpportunity.qualification_status, func.count()).group_by(
        DiscoveryOpportunity.classification, DiscoveryOpportunity.qualification_status,
    ).all()
    metrics = {"new": 0, "seller": 0, "landlord": 0, "unknown": 0, "review_required": 0, "qualified": 0, "rejected": 0}
    for category, status, count in metrics_query:
        metrics[category] = metrics.get(category, 0) + count
        if status == "review_required" or status == "unreviewed":
            metrics["review_required"] += count
        if status == "not_qualified":
            metrics["rejected"] += count
        if status == "qualified":
            metrics["qualified"] += count
    metrics["new"] = metrics["review_required"]
    return DiscoveryOpportunityListOut(items=[_serialize(db, item) for item in opportunities], total=total, metrics=metrics)


@router.get("/opportunities/{opportunity_id}", response_model=DiscoveryOpportunityOut)
def get_opportunity(opportunity_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.id == opportunity_id).first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Discovery opportunity not found")
    return _serialize(db, opportunity)


@router.get("/events", response_model=list[DiscoveryEventOut])
def list_events(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(DiscoveryEvent).order_by(DiscoveryEvent.created_at.desc()).limit(limit).all()


@router.patch("/opportunities/{opportunity_id}/review", response_model=DiscoveryOpportunityOut)
def review_opportunity(
    opportunity_id: uuid.UUID,
    payload: DiscoveryReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.classification not in CLASSIFICATIONS:
        raise HTTPException(status_code=400, detail="Invalid discovery classification")
    if payload.qualification_status not in QUALIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid qualification status")
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.id == opportunity_id).first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Discovery opportunity not found")
    opportunity.classification = payload.classification
    opportunity.qualification_status = payload.qualification_status
    opportunity.qualification_reason = payload.reason
    opportunity.reviewed_by = user.id
    opportunity.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(opportunity)
    return _serialize(db, opportunity)


def promote_qualified_opportunity(db: Session, user: User, opportunity: DiscoveryOpportunity, *, create_task: bool = True, payload: DiscoveryPromotionRequest | None = None) -> DiscoveryPromotionOut:
    """Reusable promotion flow for qualified discovery opportunities."""
    if opportunity.qualification_status != "qualified":
        raise HTTPException(status_code=409, detail="Only qualified opportunities can be promoted to CRM")
    if opportunity.classification not in {"seller", "landlord"}:
        raise HTTPException(status_code=409, detail="Only qualified seller or landlord opportunities can be promoted")
    if opportunity.property is None:
        raise HTTPException(status_code=409, detail="A property is required before promotion")

    observation = opportunity.latest_observation
    if observation is None:
        raise HTTPException(status_code=422, detail="Contact information is unavailable because no listing observation exists")
    name = observation.contact_name
    phone = normalize_phone(observation.contact_phone)
    email = normalize_email(observation.contact_email)
    if not phone and not email:
        raise HTTPException(status_code=422, detail="Contact information is missing; add or verify a phone number or email before promotion")

    contact = find_existing_contact(db, name=name, phone=phone, email=email)
    contact_created = contact is None
    if contact is None:
        contact = Contact(name=name, phone=phone, email=email, contact_type=opportunity.classification,
                          source=f"discovery:{observation.source_type or 'approved_source'}")
        db.add(contact)
        db.flush()
    if db.query(ContactProperty).filter(ContactProperty.contact_id == contact.id,
                                        ContactProperty.property_id == opportunity.property_id).first() is None:
        db.add(ContactProperty(contact_id=contact.id, property_id=opportunity.property_id))

    lead = db.query(Lead).filter(Lead.contact_id == contact.id, Lead.property_id == opportunity.property_id,
                                 Lead.lead_type == opportunity.classification).first()
    lead_created = lead is None
    if lead is None:
        lead = Lead(contact_id=contact.id, property_id=opportunity.property_id,
                    lead_type=opportunity.classification, source="discovery",
                    lead_score=opportunity.discovery_score,
                    assigned_agent_id=user.id,
                    notes=f"Promoted from discovery opportunity {opportunity.id}; source listing ID: {observation.source_listing_id or 'unavailable'}.")
        db.add(lead)
        db.flush()
        db.add(LeadStageHistory(lead_id=lead.id, from_stage=None, to_stage=lead.status))

    db.add(DiscoveryEvent(user_id=user.id, property_id=opportunity.property_id,
                           opportunity_id=opportunity.id, observation_id=observation.id,
                           event_type="crm_promoted", payload=json.dumps({
                               "lead_id": str(lead.id), "contact_id": str(contact.id),
                               "contact_created": contact_created, "lead_created": lead_created,
                               "classification": opportunity.classification,
                           })))
    task = None
    task_created = False
    planned_action = plan_intelligence_action(opportunity)
    if create_task:
        task = db.query(Task).filter(
            Task.opportunity_id == opportunity.id,
            Task.lead_id == lead.id,
            Task.status.notin_(["completed", "cancelled"]),
            Task.title == planned_action.title,
        ).first()
        if task is None:
            task = Task(
                title=planned_action.title,
                description=planned_action.description,
                assigned_user_id=lead.assigned_agent_id or user.id,
                created_by=user.id,
                lead_id=lead.id,
                contact_id=contact.id,
                opportunity_id=opportunity.id,
                priority=planned_action.priority,
            )
            db.add(task)
            db.flush()
            task_created = True

    db.add(DiscoveryEvent(user_id=user.id, property_id=opportunity.property_id,
                           opportunity_id=opportunity.id, observation_id=observation.id,
                           event_type="intelligence_action_planned" if task else "promotion_recommendation_recorded",
                           payload=json.dumps({"action": planned_action.action, "task_id": str(task.id) if task else None, "approved": bool(task), "task_created": task_created})))
    db.commit()
    if task:
        db.refresh(task)
    return DiscoveryPromotionOut(opportunity_id=opportunity.id, contact_id=contact.id, lead_id=lead.id, lead_status=lead.status,
                                 contact_created=contact_created, lead_created=lead_created,
                                 message="Discovery opportunity promoted to CRM." + (" Human-approved CRM task created." if task_created else ""),
                                 task_id=task.id if task else None,
                                 task_created=task_created,
                                 recommended_action=planned_action.action,
                                 opportunity_score=opportunity.opportunity_score,
                                 data_confidence=opportunity.data_confidence)


@router.post("/opportunities/{opportunity_id}/promote", response_model=DiscoveryPromotionOut)
def promote_opportunity(
    opportunity_id: uuid.UUID,
    payload: DiscoveryPromotionRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Explicit, auditable bridge from qualified Discovery to CRM."""
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.id == opportunity_id).with_for_update().first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Discovery opportunity not found")
    return promote_qualified_opportunity(db, user, opportunity, create_task=bool(payload and payload.create_task), payload=payload)


@router.patch("/opportunities/{opportunity_id}/contact", response_model=DiscoveryOpportunityOut)
def update_opportunity_contact(
    opportunity_id: uuid.UUID,
    payload: DiscoveryContactUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.id == opportunity_id).first()
    if opportunity is None or opportunity.latest_observation is None:
        raise HTTPException(status_code=404, detail="Discovery opportunity or listing observation not found")
    observation = opportunity.latest_observation
    if payload.name is not None:
        observation.contact_name = payload.name
    if payload.phone is not None:
        observation.contact_phone = normalize_phone(payload.phone)
    if payload.email is not None:
        observation.contact_email = normalize_email(payload.email)
    if observation.contact_name or observation.contact_phone or observation.contact_email:
        observation.contact_confidence = "medium"
    db.commit()
    db.refresh(opportunity)
    return _serialize(db, opportunity)


def _saved_search_out(db: Session, search: SavedSearch) -> SavedSearchOut:
    opportunities = db.query(DiscoveryOpportunity).join(Property).outerjoin(
        ListingObservation,
        DiscoveryOpportunity.latest_observation_id == ListingObservation.id,
    ).all()
    match_count = sum(
        1 for opportunity in opportunities
        if search.enabled and match_saved_search(search, opportunity.property, opportunity.latest_observation).matched
    )
    return SavedSearchOut.model_validate({**search.__dict__, "match_count": match_count})


@router.get("/saved-searches", response_model=list[SavedSearchOut])
def list_saved_searches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    searches = db.query(SavedSearch).filter(SavedSearch.user_id == user.id).order_by(SavedSearch.updated_at.desc()).all()
    return [_saved_search_out(db, search) for search in searches]


@router.post("/saved-searches", response_model=SavedSearchOut, status_code=201)
def create_saved_search(payload: SavedSearchCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    search = SavedSearch(user_id=user.id, **payload.model_dump())
    db.add(search)
    db.commit()
    db.refresh(search)
    return _saved_search_out(db, search)


@router.get("/saved-searches/{search_id}", response_model=SavedSearchOut)
def get_saved_search(search_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    search = db.query(SavedSearch).filter(SavedSearch.id == search_id, SavedSearch.user_id == user.id).first()
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return _saved_search_out(db, search)


@router.patch("/saved-searches/{search_id}", response_model=SavedSearchOut)
def update_saved_search(search_id: uuid.UUID, payload: SavedSearchUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    search = db.query(SavedSearch).filter(SavedSearch.id == search_id, SavedSearch.user_id == user.id).first()
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    merged = {field: getattr(search, field) for field in (
        "name", "location", "suburbs", "property_type", "min_price", "max_price",
        "listing_type", "bedrooms", "bathrooms", "minimum_score", "lead_type", "enabled",
    )}
    merged.update(payload.model_dump(exclude_unset=True))
    try:
        SavedSearchCreate(**merged)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(search, field, value)
    db.commit()
    db.refresh(search)
    return _saved_search_out(db, search)


@router.delete("/saved-searches/{search_id}", status_code=204)
def delete_saved_search(search_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    search = db.query(SavedSearch).filter(SavedSearch.id == search_id, SavedSearch.user_id == user.id).first()
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    db.delete(search)
    db.commit()
