"""Universal intake adapter for user-supplied property material.

This endpoint deliberately does not fetch third-party pages or create CRM
leads.  It records the original material, extracts only explicit facts, and
uses the established ingestion/Capture workflows where there is sufficient
identity information.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.capture import Capture
from app.models.intake_submission import IntakeSubmission
from app.models.source import Source
from app.models.property_research import PropertyResearch
from app.models.lead import Lead
from app.schemas.intake import IntakeCreate, IntakeOut
from app.services.capture_extraction import structure_listing_text
from app.services.ingestion import ingest_listing
from app.services.normalization import normalize_url
from app.services.property_research import retrieve_public_source, run_research
from app.services.property_sources import detect_property_source
from app.api.v1.endpoints.discovery import promote_qualified_opportunity

router = APIRouter()


def _listing_url(value: str) -> str:
    """Accept a public http(s) URL, never an email address/domain."""
    if "@" in value:
        raise HTTPException(status_code=422, detail="An email address is not a listing URL")
    normalized = normalize_url(value)
    parts = urlsplit(normalized or "")
    if parts.scheme not in {"http", "https"} or not parts.netloc or "." not in parts.netloc:
        raise HTTPException(status_code=422, detail="Enter a valid public listing URL")
    return normalized


def _source(db: Session) -> Source:
    source = db.query(Source).filter(Source.source_key == "universal_intake").first()
    if source is None:
        source = Source(
            name="Universal Intake", source_key="universal_intake",
            collector_type="manual_intake", environment=settings.ENVIRONMENT, is_enabled=True,
        )
        db.add(source)
        db.flush()
    return source


def _serialize(item: IntakeSubmission) -> IntakeOut:
    return IntakeOut.model_validate(item)


@router.post("/", response_model=IntakeOut, status_code=201)
def create_intake(payload: IntakeCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    capture = None
    extracted: dict = {}
    source_url = None
    raw_input = payload.value.strip() if payload.value else None
    retrieval_status = "not_requested"
    retrieval_error = None

    if payload.input_type == "screenshot":
        capture = db.query(Capture).filter(Capture.id == payload.capture_id, Capture.user_id == user.id).first()
        if capture is None:
            raise HTTPException(status_code=404, detail="Capture not found")
        extracted = dict(capture.extracted_data or {})
        source_url = _listing_url(raw_input) if raw_input else extracted.get("source_url")
        if source_url:
            retrieval_status, retrieved_text, retrieval_error = retrieve_public_source(source_url)
            # The screenshot remains the primary evidence; permitted retrieved
            # text fills only facts the screenshot did not provide.
            for field, value in structure_listing_text(retrieved_text or "").data.items():
                extracted.setdefault(field, value)
            extracted["source_url"] = source_url
    elif payload.input_type == "url":
        source_url = _listing_url(raw_input or "")
        retrieval_status, retrieved_text, retrieval_error = retrieve_public_source(source_url)
        extracted = dict(structure_listing_text(retrieved_text or "").data)
        extracted["source_url"] = source_url
    else:
        extracted = dict(structure_listing_text(raw_input or "").data)
        source_url = extracted.get("source_url")

    domain = urlsplit(source_url).netloc.lower() if source_url else None
    detected_source = detect_property_source(source_url) if source_url else None
    status = "review_required"
    result_summary = "Property captured — review required; no complete property identity was found."
    property_id = None
    opportunity_id = None
    lead_id = None
    extracted["_source_status"] = retrieval_status
    if detected_source:
        extracted["_source_provenance"] = {
            "key": detected_source.key,
            "domain": detected_source.domain,
            "adapter": detected_source.adapter,
        }
    if retrieval_error:
        extracted["_retrieval_error"] = retrieval_error
        result_summary = f"Listing research requires review: {retrieval_error}"

    # Reuse the canonical pipeline only when its existing validation can
    # establish an identity. Sparse material remains explicitly reviewable.
    if extracted.get("address") or extracted.get("listing_reference"):
        try:
            result = ingest_listing(
                db, {**extracted, "listing_url": source_url, "notes": raw_input},
                source="universal_intake", source_id=_source(db).id,
                source_metadata={
                    "source_type": detected_source.key if detected_source else "universal_intake",
                    "discovery_method": "manual_intake",
                    "source_confidence": "high" if retrieval_status == "accessed" else "medium",
                },
                created_by=user.id,
            )
            property_id = result.property_id
            status = result.outcome
            opportunity = result.opportunity
            opportunity_id = opportunity.id if opportunity else None
            if opportunity and payload.input_type == "url" and retrieval_status == "accessed" and (
                result.observation and (result.observation.contact_phone or result.observation.contact_email)
            ) and opportunity.classification in {"seller", "landlord"}:
                # This is the existing CRM gate: identified opportunity plus a
                # direct, public phone or email on its listing observation.
                opportunity.qualification_status = "qualified"
                opportunity.qualification_reason = "Automatically qualified from a retrieved public listing with a direct contact."
                promotion = promote_qualified_opportunity(db, user, opportunity, create_task=True)
                lead_id = promotion.lead_id
                status = "lead_created" if promotion.lead_created else "lead_updated"
                result_summary = "Property captured successfully — CRM lead created." if promotion.lead_created else "Property enriched successfully — existing CRM lead retained."
            elif result.outcome == "updated":
                status = "property_updated"
                result_summary = "Property enriched successfully — review required before CRM promotion."
            elif result.outcome == "created":
                status = "property_created"
                result_summary = "Property captured successfully — review required before CRM promotion."

            # The established Copilot service remains the single AI path. It
            # is optional: deterministic public-source extraction is useful
            # even if the provider is absent or temporarily unavailable.
            if result.property and retrieval_status == "accessed" and settings.ANTHROPIC_API_KEY:
                try:
                    research_lead = db.query(Lead).filter(Lead.id == lead_id).first() if lead_id else None
                    answer, evidence, research_status, original_url = run_research(
                        db, result.property, research_lead, "research_listing"
                    )
                    db.add(PropertyResearch(
                        property_id=result.property.id, lead_id=lead_id, requested_by=user.id,
                        action="research_listing", original_url=original_url,
                        source_status=research_status, source_type="original_listing",
                        evidence=evidence, result=answer,
                    ))
                    extracted["_ai_enrichment"] = "completed"
                except Exception:
                    # Do not leak provider internals or make an otherwise
                    # valid, deterministic intake fail because AI is down.
                    extracted["_ai_enrichment"] = "unavailable"
        except ValueError:
            # Intake is auditable even when a listing is intentionally sparse.
            pass

    item = IntakeSubmission(
        user_id=user.id, input_type=payload.input_type, raw_input=raw_input,
        source_url=source_url, source_domain=domain, status=status,
        result_summary=result_summary, extracted_data=extracted,
        property_id=property_id, capture_id=capture.id if capture else None,
        opportunity_id=opportunity_id, lead_id=lead_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.get("/", response_model=list[IntakeOut])
def list_intakes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return [_serialize(item) for item in db.query(IntakeSubmission).filter(IntakeSubmission.user_id == user.id).order_by(IntakeSubmission.created_at.desc()).all()]
