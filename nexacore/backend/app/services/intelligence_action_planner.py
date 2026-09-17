"""Plans human-approved CRM work from explainable opportunity intelligence."""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.models.discovery_opportunity import DiscoveryOpportunity
from app.models.task import TASK_PRIORITIES


@dataclass(frozen=True)
class PlannedAction:
    action: str
    title: str
    priority: str
    description: str


def plan_intelligence_action(opportunity: DiscoveryOpportunity) -> PlannedAction:
    score = int(opportunity.opportunity_score or 0)
    confidence = opportunity.data_confidence or "unknown"
    classification = opportunity.classification
    reasons = json.loads(opportunity.intelligence_reasons) if opportunity.intelligence_reasons else []
    evidence = "; ".join(reasons[:6]) or "No additional intelligence evidence recorded"

    if confidence in {"low", "unknown"}:
        action = "VERIFY_DATA"
        title = "Verify opportunity contact data"
        priority = "high" if score >= 60 else "medium"
    elif classification == "seller" and score >= 60:
        action = "CONTACT_OWNER"
        title = "Contact owner about selling opportunity"
        priority = "high" if score >= 80 else "medium"
    elif classification == "landlord" and score >= 60:
        action = "CONTACT_LANDLORD"
        title = "Contact landlord about rental opportunity"
        priority = "high" if score >= 80 else "medium"
    elif any("price reduction" in reason.lower() for reason in reasons):
        action = "INVESTIGATE_PRICE_CHANGE"
        title = "Investigate listing price change"
        priority = "medium"
    elif score >= 35:
        action = "FOLLOW_UP"
        title = "Follow up on discovery opportunity"
        priority = "medium"
    else:
        action = "MONITOR"
        title = "Monitor discovery opportunity"
        priority = "low"

    if priority not in TASK_PRIORITIES:
        priority = "medium"
    description = (
        f"Intelligence action: {action}\n"
        f"Opportunity score: {score}\n"
        f"Confidence: {confidence}\n"
        f"Classification: {classification}\n"
        f"Evidence: {evidence}\n"
        f"Origin: discovery opportunity {opportunity.id}"
    )
    return PlannedAction(action, title, priority, description)