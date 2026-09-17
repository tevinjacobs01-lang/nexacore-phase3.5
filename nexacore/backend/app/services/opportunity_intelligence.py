"""Explainable opportunity signals derived from persisted listing evidence."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.discovery_opportunity import DiscoveryOpportunity
from app.models.discovery_event import DiscoveryEvent
from app.models.listing_history import ListingHistory
from app.models.listing_observation import ListingObservation
from app.models.property import Property
from app.services.property_intent import score_property_intent
from app.models.hunting_profile import HuntingProfile


@dataclass(frozen=True)
class OpportunityIntelligence:
    score: int
    signal_score: int
    confidence: str
    reasons: list[str]
    next_action: str
    historical_signals: list[dict]


def _confidence(observations: list[ListingObservation]) -> str:
    if not observations:
        return "unknown"
    source_levels = {observation.source_confidence for observation in observations}
    contact_levels = {observation.contact_confidence for observation in observations}
    if "high" in source_levels and "high" in contact_levels:
        return "high"
    if "medium" in source_levels or "medium" in contact_levels or len(observations) > 1:
        return "medium"
    if "low" in source_levels or "low" in contact_levels:
        return "low"
    return "unknown"


def calculate_opportunity_intelligence(
    db: Session, opportunity: DiscoveryOpportunity
) -> OpportunityIntelligence:
    prop = opportunity.property or db.query(Property).filter(Property.id == opportunity.property_id).one()
    observations = db.query(ListingObservation).filter(
        ListingObservation.property_id == opportunity.property_id,
    ).all()
    history = db.query(ListingHistory).filter(
        ListingHistory.property_id == opportunity.property_id,
    ).all()
    latest = opportunity.latest_observation
    if latest is None and opportunity.latest_observation_id:
        latest = db.query(ListingObservation).filter(ListingObservation.id == opportunity.latest_observation_id).first()
    reasons: list[str] = []
    historical_signals: list[dict] = []
    score = 0

    def add_signal(signal_type: str, severity: str, evidence: str, detected_at=None, source_id=None):
        historical_signals.append({
            "signal_type": signal_type,
            "severity": severity,
            "detected_at": detected_at,
            "evidence": evidence,
            "confidence": _confidence(observations),
            "source_id": source_id,
        })

    classification = opportunity.classification
    if classification in {"seller", "landlord"}:
        score += 20
        reasons.append(f"{classification.title()} opportunity from listing type")
    if prop.is_owner_listed is True or prop.seller_type == "owner":
        score += 20
        reasons.append("owner-listed indicator present")

    days_on_market = prop.days_on_market
    if days_on_market is not None:
        if days_on_market >= 90:
            score += 30
            reasons.append(f"{days_on_market} days on market")
        elif days_on_market >= 60:
            score += 20
            reasons.append(f"{days_on_market} days on market")
        elif days_on_market >= 30:
            score += 10
            reasons.append(f"{days_on_market} days on market")

    reduction_items = [
        item for item in history
        if item.previous_price is not None and item.new_price is not None
        and float(item.new_price) < float(item.previous_price)
    ]
    reductions = len(reduction_items)
    if reductions:
        original_price = next(
            (item.previous_price for item in sorted(history, key=lambda item: item.changed_at or datetime.min)
             if item.previous_price is not None),
            None,
        )
        current_price = prop.asking_price or prop.monthly_rental
        reduction_pct = (
            ((float(original_price) - float(current_price)) / float(original_price)) * 100
            if original_price and current_price and float(original_price) > 0 else None
        )
        reduction_evidence = f"{reductions} recorded price reduction{'s' if reductions != 1 else ''}"
        if reduction_pct is not None:
            reduction_evidence += f"; cumulative reduction {reduction_pct:.1f}%"
        add_signal(
            "PRICE_REDUCTION",
            "high" if reductions >= 2 or (reduction_pct is not None and reduction_pct >= 10) else "medium",
            reduction_evidence,
            max((item.changed_at for item in reduction_items if item.changed_at), default=None),
            latest.source_id if latest else None,
        )
        reasons.append(reduction_evidence)
        score += min(20, reductions * 10)

    if days_on_market is not None and days_on_market >= 90:
        add_signal("STALE_LISTING", "high", f"{days_on_market} days on market", latest.last_seen_at if latest else None, latest.source_id if latest else None)
    elif days_on_market is not None and days_on_market >= 60:
        add_signal("STALE_LISTING", "medium", f"{days_on_market} days on market", latest.last_seen_at if latest else None, latest.source_id if latest else None)

    status_changes = [item for item in history if item.previous_status != item.new_status and (item.previous_status or item.new_status)]
    if status_changes:
        add_signal("STATUS_CHANGE", "medium", f"{len(status_changes)} listing status change{'s' if len(status_changes) != 1 else ''}", max((item.changed_at for item in status_changes if item.changed_at), default=None))
        reasons.append(f"{len(status_changes)} listing status change{'s' if len(status_changes) != 1 else ''} recorded")
        score += 5

    description_changes = [item for item in history if item.previous_description != item.new_description and (item.previous_description or item.new_description)]
    if description_changes:
        add_signal("DESCRIPTION_CHANGE", "low", f"{len(description_changes)} meaningful description change{'s' if len(description_changes) != 1 else ''}", max((item.changed_at for item in description_changes if item.changed_at), default=None))
        reasons.append(f"{len(description_changes)} meaningful description change{'s' if len(description_changes) != 1 else ''}")

    relist_count = db.query(DiscoveryEvent).filter(
        DiscoveryEvent.property_id == opportunity.property_id,
        DiscoveryEvent.event_type == "relisted",
    ).count()
    if relist_count:
        add_signal("RELISTED", "high" if relist_count > 1 else "medium", f"{relist_count} relist event{'s' if relist_count != 1 else ''} recorded", latest.last_seen_at if latest else None, latest.source_id if latest else None)
        reasons.append(f"{relist_count} relist event{'s' if relist_count != 1 else ''} recorded")
        score += min(15, relist_count * 10)

    if len({observation.source_id for observation in observations}) > 1:
        add_signal("CROSS_SOURCE_CONFIRMATION", "high", f"Observed across {len({observation.source_id for observation in observations})} sources", latest.last_seen_at if latest else None)
        reasons.append("same property observed across multiple sources")
        score += 10

    # Price reductions and relists are scored once here; the remaining checks
    # below retain the existing opportunity weighting without duplicate bonuses.
    if prop.is_relisted or (latest and latest.lifecycle_status == "relisted"):
        if not relist_count:
            add_signal("RELISTED", "medium", "Current observation is relisted", latest.last_seen_at if latest else None, latest.source_id if latest else None)
            reasons.append("relisting signal recorded")
            score += 15

    recent_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)
    last_seen_at = latest.last_seen_at if latest else None
    if last_seen_at and last_seen_at.tzinfo:
        last_seen_at = last_seen_at.replace(tzinfo=None)
    if last_seen_at and last_seen_at >= recent_cutoff:
        score += 5
        reasons.append("recent listing activity")

    confidence = _confidence(observations)
    profile = db.query(HuntingProfile).first()
    target_locations = []
    if profile and profile.enabled:
        target_locations = json.loads(profile.target_locations)
    intent_score = score_property_intent(prop.notes, {
        "listing_type": prop.listing_type,
        "address": prop.address,
        "suburb": prop.suburb,
        "city": prop.city,
        "province": prop.province,
        "property_type": prop.property_type,
        "asking_price": prop.asking_price,
        "monthly_rental": prop.monthly_rental,
        "contact_number": prop.contact_number,
        "email": prop.email,
        "advertiser_type": prop.seller_type,
    }, target_locations=target_locations)
    if intent_score.score:
        score += min(20, intent_score.score // 5)
        reasons.extend(intent_score.reasons[:3])
    if intent_score.missing_information:
        reasons.append("missing information: " + ", ".join(intent_score.missing_information))
    if confidence == "high":
        score += 10
        reasons.append("high source and contact confidence")
    elif confidence == "medium":
        score += 5
        reasons.append("medium source or contact confidence")

    score = min(100, score)
    next_action = (
        "CONTACT_OWNER" if classification == "seller" and confidence in {"high", "medium"} and (reductions or prop.is_owner_listed)
        else "CONTACT_LANDLORD" if classification == "landlord" and confidence in {"high", "medium"} and (reductions or prop.is_owner_listed)
        else "INVESTIGATE_PRICE_CHANGE" if reductions
        else "VERIFY_DATA" if confidence in {"low", "unknown"}
        else "FOLLOW_UP" if classification in {"seller", "landlord"}
        else "MONITOR"
    )
    return OpportunityIntelligence(score, min(100, score), confidence, reasons, next_action, historical_signals)


def recompute_opportunity_intelligence(
    db: Session, opportunity: DiscoveryOpportunity
) -> OpportunityIntelligence:
    intelligence = calculate_opportunity_intelligence(db, opportunity)
    opportunity.opportunity_score = intelligence.score
    opportunity.signal_score = intelligence.signal_score
    opportunity.data_confidence = intelligence.confidence
    opportunity.intelligence_reasons = json.dumps(intelligence.reasons)
    opportunity.recommended_action = intelligence.next_action
    db.add(opportunity)
    return intelligence