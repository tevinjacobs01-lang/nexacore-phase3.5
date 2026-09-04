"""
Unified Lead/Opportunity inbox endpoint.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.contact import Contact
<<<<<<< HEAD
from app.models.lead import Lead
from app.models.property import Property
from app.models.user import User

try:
    from app.models.discovery_opportunity import DiscoveryOpportunity
except ModuleNotFoundError:
    DiscoveryOpportunity = None

try:
    from app.services.next_action import derive_next_action
except ModuleNotFoundError:
    derive_next_action = None
=======
from app.models.lead import Lead
from app.models.property import Property
from app.models.user import User

try:
    from app.models.discovery_opportunity import DiscoveryOpportunity
except ModuleNotFoundError:
    DiscoveryOpportunity = None

try:
    from app.services.next_action import derive_next_action
except ModuleNotFoundError:
    derive_next_action = None
>>>>>>> 1d97f50 (Make leads inbox compatible with production master)

router = APIRouter()


@router.get("/inbox")
def leads_inbox(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Unified Lead + Opportunity inbox for Dashboard and Leads page.
    
    Returns both active CRM Leads and unqualified DiscoveryOpportunities
    in a single response with type indicators.
    """
    
    # Query active Leads
    lead_query = db.query(Lead).join(Contact).outerjoin(Property)
    if user.role != "admin":
        lead_query = lead_query.filter(Lead.assigned_agent_id == user.id)
    
    leads = lead_query.order_by(Lead.created_at.desc()).all()
    
    # Query unqualified Opportunities
<<<<<<< HEAD
    opportunities = []
    if DiscoveryOpportunity is not None:
        opportunities = (
            db.query(DiscoveryOpportunity)
            .join(Property)
            .filter(
                DiscoveryOpportunity.qualification_status.in_(
                    ["unreviewed", "review_required"]
                )
            )
            .order_by(DiscoveryOpportunity.created_at.desc())
            .all()
        )
=======
    opportunities = []
    if DiscoveryOpportunity is not None:
        opportunities = (
            db.query(DiscoveryOpportunity)
            .join(Property)
            .filter(
                DiscoveryOpportunity.qualification_status.in_(
                    ["unreviewed", "review_required"]
                )
            )
            .order_by(DiscoveryOpportunity.created_at.desc())
            .all()
        )
>>>>>>> 1d97f50 (Make leads inbox compatible with production master)
    
    # Synthesize items
    items = []
    
    for lead in leads:
<<<<<<< HEAD
        if derive_next_action is not None:
            action = derive_next_action(db, lead)
            next_action = {
                "action_type": action.action_type,
                "action_label": action.action_label,
                "urgency": action.urgency,
                "due_at": action.due_at,
                "reason": action.reason,
            }
        else:
            next_action = {
                "action_type": "review_lead",
                "action_label": "Review lead",
                "urgency": "medium",
                "due_at": None,
                "reason": "Awaiting follow-up",
            }
=======
        if derive_next_action is not None:
            action = derive_next_action(db, lead)
            next_action = {
                "action_type": action.action_type,
                "action_label": action.action_label,
                "urgency": action.urgency,
                "due_at": action.due_at,
                "reason": action.reason,
            }
        else:
            next_action = {
                "action_type": "review_lead",
                "action_label": "Review lead",
                "urgency": "medium",
                "due_at": None,
                "reason": "Awaiting follow-up",
            }
>>>>>>> 1d97f50 (Make leads inbox compatible with production master)
        contact = db.query(Contact).filter(Contact.id == lead.contact_id).first()
        prop = db.query(Property).filter(Property.id == lead.property_id).first() if lead.property_id else None
        items.append({
            "type": "lead",
            "id": str(lead.id),
            "contact_name": contact.name if contact else None,
            "property_address": prop.address if prop else None,
            "property_suburb": prop.suburb if prop else None,
            "source": lead.source or "unknown",
            "status": lead.status,
            "lead_score": lead.lead_score,
            "priority": lead.priority,
<<<<<<< HEAD
            "next_action": next_action,
=======
            "next_action": next_action,
>>>>>>> 1d97f50 (Make leads inbox compatible with production master)
            "workflow_action": "manage_pipeline",
        })
    
    for opp in opportunities:
        prop = db.query(Property).filter(Property.id == opp.property_id).first()
        obs = opp.latest_observation
        source_key = "unknown"
        if obs and obs.source:
            source_key = obs.source.source_key
        
        items.append({
            "type": "opportunity",
            "id": str(opp.id),
            "contact_name": obs.contact_name if obs else None,
            "property_address": prop.address if prop else None,
            "property_suburb": prop.suburb if prop else None,
            "source": "discovery",
            "source_key": source_key,
            "status": opp.qualification_status,
            "classification": opp.classification,
            "lead_score": prop.lead_score if prop else 0,
            "opportunity_score": opp.opportunity_score,
            "next_action": {
                "action_type": "review_opportunity",
                "action_label": f"Review {opp.classification or 'opportunity'}: {prop.address if prop else 'property'}",
                "urgency": "high" if opp.qualification_status == "review_required" else "medium",
                "due_at": None,
                "reason": "Awaiting qualification",
            },
            "workflow_action": "review_and_qualify",
        })
    
    # Sort by urgency
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    items.sort(key=lambda i: (
        urgency_order.get(i.get("next_action", {}).get("urgency", "none"), 5),
        i.get("next_action", {}).get("due_at") or datetime.max,
    ))
    
    return {
        "items": items,
        "total": len(items),
        "metrics": {
            "total_leads": sum(1 for i in items if i["type"] == "lead"),
            "awaiting_review": sum(1 for i in items if i["type"] == "opportunity"),
            "by_source": {},
        }
    }
