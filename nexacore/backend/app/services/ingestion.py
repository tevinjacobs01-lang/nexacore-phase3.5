"""Canonical property ingestion for imports and approved collectors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.collectors.base import Listing
from app.models.duplicate_match import DuplicateMatch
from app.models.discovery_event import DiscoveryEvent
from app.models.discovery_opportunity import DiscoveryOpportunity
from app.models.listing_observation import ListingObservation
from app.models.listing_history import ListingHistory
from app.models.property import Property
from app.models.saved_search import SavedSearch
from app.services.dedupe import classify_duplicate, DuplicateClassification
from app.services.discovery_qualification import classify_listing, qualify_listing
from app.services import normalization as norm
from app.services.scoring_engine import recompute_score
from app.services.opportunity_intelligence import recompute_opportunity_intelligence


PROPERTY_FIELDS = (
    "listing_reference", "address", "suburb", "city", "province", "postal_code",
    "latitude", "longitude", "listing_type", "property_type", "bedrooms",
    "seller_type", "is_owner_listed",
    "bathrooms", "garages", "floor_size_sqm", "stand_size_sqm", "asking_price",
    "monthly_rental", "listing_date", "days_on_market", "listing_source",
    "listing_url", "agent_name", "contact_number", "email", "notes",
    "listing_status",
)


@dataclass
class IngestionResult:
    property: Property | None
    outcome: str
    source: str | None = None
    duplicate_classification: str | None = None
    duplicate_reason: str | None = None
    price_changed: bool = False
    status_changed: bool = False
    relisted: bool = False
    score_changed: bool = False
    observation: ListingObservation | None = None
    opportunity: DiscoveryOpportunity | None = None

    @property
    def property_id(self):
        return self.property.id if self.property else None


def canonicalize_url(value: str | None) -> str | None:
    """Normalize a listing URL without fetching or resolving it."""
    normalized = norm.normalize_url(value)
    if not normalized:
        return None
    parts = urlsplit(normalized)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith(("utm_", "fbclid"))]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def _get(candidate: Listing | dict[str, Any], field: str, default=None):
    if isinstance(candidate, dict):
        return candidate.get(field, default)
    return getattr(candidate, field, default)


def _normalized_candidate(candidate: Listing | dict[str, Any], source: str | None) -> dict[str, Any]:
    values = {field: _get(candidate, field) for field in PROPERTY_FIELDS}
    values["listing_reference"] = values["listing_reference"] or _get(candidate, "source_listing_id")
    values["address"] = str(values["address"]).strip() if values["address"] else None
    values["suburb"] = norm.normalize_suburb(values["suburb"])
    values["city"] = norm.normalize_city(values["city"])
    values["province"] = norm.normalize_province(values["province"])
    values["property_type"] = norm.normalize_property_type(values["property_type"])
    values["listing_type"] = values["listing_type"].strip().lower() if isinstance(values["listing_type"], str) else values["listing_type"]
    values["contact_number"] = norm.normalize_phone(values["contact_number"])
    values["email"] = norm.normalize_email(values["email"])
    values["listing_url"] = canonicalize_url(values["listing_url"])
    values["listing_source"] = source or values["listing_source"]
    values["listing_status"] = values["listing_status"] or _get(candidate, "status")
    values["notes"] = values["notes"] or _get(candidate, "description")
    return values


def _candidate_pool(db: Session, values: dict[str, Any]) -> list[Property]:
    identity_filters = []
    if values.get("listing_reference"):
        identity_filters.append(Property.listing_reference == values["listing_reference"])
    if values.get("listing_url"):
        identity_filters.append(Property.listing_url == values["listing_url"])
    if values.get("address") and values.get("suburb"):
        identity_filters.append(
            (Property.address.ilike(values["address"])) & (Property.suburb.ilike(values["suburb"]))
        )
    if values.get("contact_number"):
        identity_filters.append(Property.contact_number == values["contact_number"])
    if values.get("email"):
        identity_filters.append(Property.email == values["email"])
    if not identity_filters:
        return []
    return db.query(Property).filter(or_(*identity_filters)).all()


def _same_value(existing, incoming) -> bool:
    if existing is None or incoming is None:
        return existing == incoming
    if isinstance(existing, (int, float)) or hasattr(existing, "as_tuple"):
        try:
            return float(existing) == float(incoming)
        except (TypeError, ValueError):
            pass
    return existing == incoming


def _source_metadata(candidate: Listing | dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    values = metadata.copy() if metadata else {}
    for key in (
        "source_listing_id", "source_type", "discovery_method", "source_confidence",
        "contact_name", "contact_phone", "contact_email", "contact_company",
        "contact_agency", "contact_confidence", "source_updated_at",
    ):
        if not values.get(key):
            candidate_value = _get(candidate, key)
            if candidate_value:
                values[key] = candidate_value
    if not values.get("contact_phone"):
        values["contact_phone"] = _get(candidate, "contact_number")
    if not values.get("contact_email"):
        values["contact_email"] = _get(candidate, "email")
    if not values.get("contact_name"):
        values["contact_name"] = _get(candidate, "agent_name")
    raw = _get(candidate, "raw", {}) or {}
    if isinstance(raw, dict):
        for key in (
            "source_listing_id", "source_type", "discovery_method", "source_confidence",
            "contact_name", "contact_phone", "contact_email", "contact_company",
            "contact_agency", "contact_confidence", "source_updated_at",
        ):
            if not values.get(key) and raw.get(key):
                values[key] = raw[key]
    return values


def _trim_raw_payload(candidate: Listing | dict[str, Any]) -> str | None:
    raw = _get(candidate, "raw")
    if not isinstance(raw, dict) or not raw:
        return None
    try:
        return json.dumps(raw, default=str)[:10000]
    except (TypeError, ValueError):
        return None


def _event_exists(db: Session, event_type: str, property_id, observation_id=None) -> bool:
    query = db.query(DiscoveryEvent).filter(
        DiscoveryEvent.event_type == event_type,
        DiscoveryEvent.property_id == property_id,
    )
    if observation_id is not None:
        query = query.filter(DiscoveryEvent.observation_id == observation_id)
    return query.first() is not None


def _create_saved_search_events(db: Session, prop: Property, opportunity: DiscoveryOpportunity, observation: ListingObservation | None, event_types: list[str]) -> None:
    if observation is None or not event_types:
        return
    searches = db.query(SavedSearch).filter(SavedSearch.enabled.is_(True)).all()
    for search in searches:
        from app.services.discovery_search import match_saved_search

        if not match_saved_search(search, prop, observation).matched:
            continue
        event_type = f"{search.lead_type}_match"
        payload = json.dumps({"saved_search_id": str(search.id), "trigger": event_types[-1]})
        existing = db.query(DiscoveryEvent).filter(
            DiscoveryEvent.event_type == event_type,
            DiscoveryEvent.property_id == prop.id,
            DiscoveryEvent.opportunity_id == opportunity.id,
            DiscoveryEvent.payload == payload,
        ).first()
        if existing is None:
            db.add(DiscoveryEvent(
                user_id=search.user_id,
                property_id=prop.id,
                opportunity_id=opportunity.id,
                observation_id=observation.id,
                event_type=event_type,
                payload=payload,
            ))


def _upsert_observation(
    db: Session,
    prop: Property,
    candidate: Listing | dict[str, Any],
    source_id,
    metadata: dict[str, Any],
    price_changed: bool,
    relisted: bool,
) -> tuple[ListingObservation | None, list[str]]:
    if source_id is None:
        return None, []

    source_listing_id = metadata.get("source_listing_id") or _get(candidate, "source_listing_id") or _get(candidate, "listing_reference")
    canonical_url = canonicalize_url(_get(candidate, "listing_url"))
    observation = None
    if source_listing_id:
        observation = db.query(ListingObservation).filter(
            ListingObservation.source_id == source_id,
            ListingObservation.source_listing_id == source_listing_id,
        ).first()
    if observation is None and canonical_url:
        observation = db.query(ListingObservation).filter(
            ListingObservation.source_id == source_id,
            ListingObservation.canonical_url == canonical_url,
        ).first()

    now = datetime.now().astimezone()
    previous_status = observation.lifecycle_status if observation else None
    if observation is None:
        lifecycle_status = "new"
        observation = ListingObservation(
            source_id=source_id,
            property_id=prop.id,
            source_listing_id=source_listing_id,
            canonical_url=canonical_url,
            source_type=metadata.get("source_type"),
            discovery_method=metadata.get("discovery_method"),
            source_confidence=metadata.get("source_confidence") or "unknown",
            contact_name=metadata.get("contact_name"),
            contact_phone=metadata.get("contact_phone"),
            contact_email=metadata.get("contact_email"),
            contact_company=metadata.get("contact_company"),
            contact_agency=metadata.get("contact_agency"),
            contact_confidence=metadata.get("contact_confidence") or "unknown",
            lifecycle_status=lifecycle_status,
            observed_at=now,
            first_seen_at=now,
            last_seen_at=now,
            source_updated_at=metadata.get("source_updated_at"),
            raw_payload=_trim_raw_payload(candidate),
        )
        db.add(observation)
        db.flush()
        event_types = ["new_listing"]
    else:
        observation.property_id = prop.id
        observation.observed_at = now
        observation.last_seen_at = now
        if metadata.get("source_updated_at"):
            observation.source_updated_at = metadata["source_updated_at"]
        event_types = []
        if previous_status in ("removed", "expired"):
            observation.lifecycle_status = "relisted"
            event_types.append("relisted")
        elif price_changed:
            observation.lifecycle_status = "price_changed"
            event_types.append("price_changed")
        else:
            observation.lifecycle_status = "active"

        for field in (
            "canonical_url", "source_type", "discovery_method", "contact_name", "contact_phone",
            "contact_email", "contact_company", "contact_agency", "raw_payload",
        ):
            value = canonical_url if field == "canonical_url" else metadata.get(field)
            if value:
                setattr(observation, field, value)
        for field in ("source_confidence", "contact_confidence"):
            if metadata.get(field) and metadata[field] != "unknown":
                setattr(observation, field, metadata[field])
        if relisted and "relisted" not in event_types:
            event_types.append("relisted")
    return observation, event_types


def _upsert_opportunity(db: Session, prop: Property, observation: ListingObservation | None):
    if observation is None:
        return None, []
    classification = classify_listing(prop)
    qualification = qualify_listing(prop, observation)
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.property_id == prop.id).first()
    new_opportunity = opportunity is None
    if opportunity is None:
        opportunity = DiscoveryOpportunity(property_id=prop.id)
        db.add(opportunity)
    opportunity.latest_observation = observation
    opportunity.classification = classification
    opportunity.qualification_status = qualification.status
    opportunity.qualification_reason = qualification.reason
    opportunity.discovery_score = qualification.score
    recompute_opportunity_intelligence(db, opportunity)
    if new_opportunity:
        return opportunity, [f"new_{classification}_opportunity"] if classification != "unknown" else []
    return opportunity, []


def ingest_listing(
    db: Session,
    candidate: Listing | dict[str, Any],
    source: str | None = None,
    address_fallback: bool = False,
    source_id=None,
    source_metadata: dict[str, Any] | None = None,
    created_by=None,
) -> IngestionResult:
    """Normalize, deduplicate, persist, history-track, and score one listing."""
    values = _normalized_candidate(candidate, source)
    metadata = _source_metadata(candidate, source_metadata)
    problems = norm.validate_listing(values)
    if source_metadata and source_metadata.get("source_type") == "social" and norm.has_meaningful_property_intent({**values, **source_metadata}):
        problems = [problem for problem in problems if problem != "missing both address and listing_reference"]
    if problems:
        raise ValueError("; ".join(problems))

    pool = _candidate_pool(db, values)
    exact: Property | None = None
    duplicate: tuple[Property, DuplicateClassification] | None = None
    for existing in pool:
        classification = classify_duplicate(values, existing)
        if classification.match_type == "exact":
            exact = existing
            break
        if classification.match_type != "unique" and duplicate is None:
            duplicate = (existing, classification)

    # A bare address+suburb match is the importer's established fallback identity.
    existing = exact or (
        duplicate[0]
        if address_fallback and duplicate and duplicate[1].match_type == "possible"
        else None
    )
    if duplicate and not exact and duplicate[1].match_type in ("likely", "possible") and existing is None:
        property_payload = {field: values[field] for field in PROPERTY_FIELDS if values[field] is not None}
        if created_by is not None:
            property_payload["created_by"] = created_by
        new_property = Property(**property_payload)
        db.add(new_property)
        db.flush()
        db.add(DuplicateMatch(
            property_id=new_property.id,
            matched_property_id=duplicate[0].id,
            match_type=duplicate[1].match_type,
            match_reason=duplicate[1].reason,
        ))
        old_score = new_property.lead_score
        recompute_score(db, new_property)
        observation, event_types = _upsert_observation(db, new_property, candidate, source_id, metadata, False, False)
        opportunity, opportunity_events = _upsert_opportunity(db, new_property, observation)
        for event_type in event_types + opportunity_events:
            if not _event_exists(db, event_type, new_property.id, observation.id if observation else None):
                db.add(DiscoveryEvent(property_id=new_property.id, opportunity_id=opportunity.id if opportunity else None, observation_id=observation.id if observation else None, event_type=event_type))
        _create_saved_search_events(db, new_property, opportunity, observation, event_types + opportunity_events)
        return IngestionResult(
            property=new_property,
            outcome="review_required",
            source=values.get("listing_source"),
            duplicate_classification=duplicate[1].match_type,
            duplicate_reason=duplicate[1].reason,
            score_changed=old_score != new_property.lead_score,
            observation=observation,
            opportunity=opportunity,
        )

    if existing is None:
        property_payload = {field: values[field] for field in PROPERTY_FIELDS if values[field] is not None}
        if created_by is not None:
            property_payload["created_by"] = created_by
        existing = Property(**property_payload)
        db.add(existing)
        db.flush()
        old_score = existing.lead_score
        recompute_score(db, existing)
        observation, event_types = _upsert_observation(db, existing, candidate, source_id, metadata, False, False)
        opportunity, opportunity_events = _upsert_opportunity(db, existing, observation)
        for event_type in event_types + opportunity_events:
            if not _event_exists(db, event_type, existing.id, observation.id if observation else None):
                db.add(DiscoveryEvent(property_id=existing.id, opportunity_id=opportunity.id if opportunity else None, observation_id=observation.id if observation else None, event_type=event_type))
        _create_saved_search_events(db, existing, opportunity, observation, event_types + opportunity_events)
        return IngestionResult(
            property=existing,
            outcome="created",
            source=values.get("listing_source"),
            score_changed=old_score != existing.lead_score,
            observation=observation,
            opportunity=opportunity,
        )

    if created_by is not None and existing.created_by is None:
        existing.created_by = created_by

    old_price = existing.asking_price if existing.asking_price is not None else existing.monthly_rental
    new_price = values.get("asking_price") if values.get("asking_price") is not None else values.get("monthly_rental")
    price_changed = new_price is not None and old_price is not None and float(new_price) != float(old_price)
    new_status = values.get("listing_status")
    status_changed = new_status is not None and new_status != existing.listing_status
    relisted = bool(
        values.get("days_on_market") is not None
        and existing.days_on_market is not None
        and values["days_on_market"] < existing.days_on_market - 5
        and values.get("listing_date") and existing.listing_date
        and values["listing_date"] > existing.listing_date
    )
    if price_changed and float(new_price) < float(old_price):
        existing.previous_asking_price = existing.asking_price
        existing.price_reduced_at = datetime.now(timezone.utc)
    if relisted:
        existing.is_relisted = True

    history_needed = price_changed or status_changed or values.get("notes") not in (None, existing.notes)
    if history_needed:
        db.add(ListingHistory(
            property_id=existing.id,
            previous_price=old_price,
            new_price=new_price,
            previous_description=existing.notes,
            new_description=values.get("notes"),
            previous_status=existing.listing_status,
            new_status=new_status,
        ))

    changed = relisted or price_changed or status_changed
    for field in PROPERTY_FIELDS:
        value = values.get(field)
        if value is not None and not _same_value(getattr(existing, field), value):
            setattr(existing, field, value)
            changed = True
    old_score = existing.lead_score
    if changed:
        recompute_score(db, existing)
    observation, event_types = _upsert_observation(db, existing, candidate, source_id, metadata, price_changed, relisted)
    opportunity, opportunity_events = _upsert_opportunity(db, existing, observation)
    for event_type in event_types + opportunity_events:
        if not _event_exists(db, event_type, existing.id, observation.id if observation else None):
            db.add(DiscoveryEvent(property_id=existing.id, opportunity_id=opportunity.id if opportunity else None, observation_id=observation.id if observation else None, event_type=event_type))
    _create_saved_search_events(db, existing, opportunity, observation, event_types + opportunity_events)
    return IngestionResult(
        property=existing,
        outcome="updated" if changed else "unchanged",
        source=values.get("listing_source"),
        duplicate_classification="exact" if exact else None,
        price_changed=price_changed,
        status_changed=status_changed,
        relisted=relisted,
        score_changed=changed and old_score != existing.lead_score,
        observation=observation,
        opportunity=opportunity,
    )