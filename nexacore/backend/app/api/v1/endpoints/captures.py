import json
import uuid
from datetime import datetime, timezone

import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.capture import Capture
from app.models.discovery_opportunity import DiscoveryOpportunity
from app.models.contact import Contact
from app.models.contact_property import ContactProperty
from app.models.listing_observation import ListingObservation
from app.models.property import Property
from app.models.source import Source
from app.models.task import Task
from app.models.lead import Lead
from app.models.lead_stage_history import LeadStageHistory
from app.schemas.capture import CaptureOut, CaptureReview
from app.services.capture_extraction import extract_listing_image
from app.services.discovery_qualification import qualify_listing
from app.services.object_storage import get_object, new_object_key, put_object, remove_object
from app.services.scoring_engine import recompute_score
from app.services.contact_dedupe import find_existing_contact
from app.services.normalization import normalize_email, normalize_phone
from app.services.opportunity_intelligence import recompute_opportunity_intelligence
from app.api.v1.endpoints.discovery import promote_qualified_opportunity, promotion_state

router = APIRouter()


def _capture_review_status(capture: Capture) -> str:
    if capture.status == "declined":
        return "declined"
    if capture.status == "saved":
        return "reviewed_saved"
    return "review_required"


def _serialize_capture(db: Session, capture: Capture) -> dict:
    opportunity = (
        db.query(DiscoveryOpportunity)
        .filter(DiscoveryOpportunity.id == capture.opportunity_id)
        .first()
        if capture.opportunity_id
        else None
    )
    if opportunity is not None:
        state = promotion_state(db, opportunity)
    elif capture.status == "declined":
        state = {
            "crm_status": "not_promoted",
            "promotion_eligible": False,
            "promotion_block_reason": "Capture was declined.",
            "lead_id": None,
            "lead_status": None,
        }
    else:
        state = {
            "crm_status": "not_promoted",
            "promotion_eligible": False,
            "promotion_block_reason": "Review the capture before CRM promotion.",
            "lead_id": None,
            "lead_status": None,
        }
    return {
        "id": capture.id,
        "user_id": capture.user_id,
        "original_filename": capture.original_filename,
        "content_type": capture.content_type,
        "status": capture.status,
        "extraction_method": capture.extraction_method,
        "extracted_data": capture.extracted_data,
        "extraction_notes": capture.extraction_notes,
        "extraction_status": (capture.extracted_data or {}).get("_extraction_status", "review_required"),
        "extracted_field_confidence": (capture.extracted_data or {}).get("_field_confidence", {}),
        "extracted_candidates": (capture.extracted_data or {}).get("_candidates", {}),
        "raw_text_detected": bool((capture.extracted_data or {}).get("_raw_text_detected")),
        "property_id": capture.property_id,
        "contact_id": capture.contact_id,
        "opportunity_id": capture.opportunity_id,
        "review_status": _capture_review_status(capture),
        "qualification_status": opportunity.qualification_status if opportunity else None,
        "classification": opportunity.classification if opportunity else None,
        "created_at": capture.created_at,
        "updated_at": capture.updated_at,
        **state,
    }


@router.post("/", response_model=CaptureOut, status_code=201)
async def create_capture(
    files: list[UploadFile] = File(...),
    visible_text: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one image is required")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="A capture can include up to 10 images")

    valid_files = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="Capture requires image files only")
        image = await file.read()
        from app.core.config import settings
        if len(image) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Capture image exceeds the upload limit")
        valid_files.append((file, image))

    # Multi-image capture is a single capture record grouped by the upload operation.
    first_file, first_image = valid_files[0]
    try:
        extraction = extract_listing_image(first_image, first_file.content_type, visible_text)
        extracted = extraction.data
        notes = extraction.notes
        extracted["_field_confidence"] = extraction.field_confidence
        extracted["_candidates"] = extraction.candidates
        extracted["_raw_text_detected"] = bool(extraction.raw_text)
        extracted["_extraction_status"] = "fields_populated" if extraction.data else "review_required"
        extraction_method = extraction.method
    except RuntimeError as exc:
        extracted = {
            "_field_confidence": {},
            "_candidates": {},
            "_raw_text_detected": False,
            "_extraction_status": "unavailable",
        }
        notes = [str(exc), "Review the listing manually or configure an OCR/Vision provider."]
        extraction_method = "provider_unavailable"
    primary_filename = first_file.filename or "capture"
    stored = put_object(first_image, primary_filename, new_object_key(primary_filename, "captures"), first_file.content_type)

    capture = Capture(
        user_id=user.id,
        original_filename=primary_filename,
        storage_path=stored.key, object_key=stored.key,
        storage_provider=stored.provider, storage_bucket=stored.bucket,
        content_type=first_file.content_type,
        extracted_data=extracted,
        extraction_notes=" ".join(notes),
        extraction_method=extraction_method,
    )
    db.add(capture)
    db.flush()

    from app.models.attachment import Attachment
    for file_obj, image_bytes in valid_files:
        original_filename = file_obj.filename or "capture"
        stored_obj = put_object(image_bytes, original_filename, new_object_key(original_filename, "captures"), file_obj.content_type)
        attachment = Attachment(
            entity_type="capture",
            entity_id=capture.id,
            original_filename=original_filename,
            storage_path=stored_obj.key,
            object_key=stored_obj.key,
            storage_provider=stored_obj.provider,
            storage_bucket=stored_obj.bucket,
            content_type=file_obj.content_type,
            size_bytes=len(image_bytes),
            uploaded_by=user.id,
        )
        db.add(attachment)

    db.commit()
    db.refresh(capture)
    return _serialize_capture(db, capture)


@router.get("/", response_model=list[CaptureOut])
def list_captures(db: Session = Depends(get_db), user=Depends(get_current_user)):
    captures = db.query(Capture).filter(Capture.user_id == user.id).order_by(Capture.created_at.desc()).all()
    return [_serialize_capture(db, capture) for capture in captures]


@router.get("/{capture_id}/evidence")
def capture_evidence(capture_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    capture = db.query(Capture).filter(Capture.id == capture_id, Capture.user_id == user.id).first()
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    return StreamingResponse(
        io.BytesIO(get_object(capture.object_key or capture.storage_path, capture.storage_provider, capture.storage_bucket)),
        media_type=capture.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{capture.original_filename}"'},
    )


@router.patch("/{capture_id}", response_model=CaptureOut)
def review_capture(capture_id: uuid.UUID, payload: CaptureReview, db: Session = Depends(get_db), user=Depends(get_current_user)):
    capture = db.query(Capture).filter(Capture.id == capture_id, Capture.user_id == user.id).first()
    if capture is None: raise HTTPException(status_code=404, detail="Capture not found")
    data = payload.extracted_data.model_dump()
    metadata = {key: value for key, value in (capture.extracted_data or {}).items() if key.startswith("_")}
    if data.get("listing_type") not in {"sale", "rent"}: raise HTTPException(status_code=422, detail="Listing type must be sale or rent")
    if data.get("listing_type") == "sale" and data.get("asking_price") is None: raise HTTPException(status_code=422, detail="Sale price is required before saving")
    if data.get("listing_type") == "rent" and data.get("monthly_rental") is None: raise HTTPException(status_code=422, detail="Monthly rental is required before saving")

    property_data = {key: value for key, value in data.items() if key in {"address", "suburb", "city", "province", "postal_code", "listing_type", "property_type", "asking_price", "monthly_rental", "bedrooms", "bathrooms", "garages", "floor_size_sqm", "stand_size_sqm", "notes", "seller_type", "is_owner_listed", "contact_number", "email", "listing_reference", "agent_name"} and value is not None}
    if data.get("source_url"):
        property_data["listing_url"] = data["source_url"]
    property_data.setdefault("listing_source", "screenshot_capture")
    property_data["created_by"] = user.id

    prop = db.query(Property).filter(
        Property.address == data.get("address"),
        Property.suburb == data.get("suburb"),
        Property.listing_type == data.get("listing_type"),
    ).first()
    if prop is None:
        prop = Property(**property_data)
        db.add(prop)
        db.flush()
    else:
        for field, value in property_data.items():
            setattr(prop, field, value)

    contact = None
    contact_name = data.get("contact_name")
    contact_phone = normalize_phone(data.get("contact_number"))
    contact_email = normalize_email(data.get("email"))
    if contact_name or contact_phone or contact_email:
        contact = find_existing_contact(db, name=contact_name, phone=contact_phone, email=contact_email)
        if contact is None:
            contact = Contact(name=contact_name, phone=contact_phone, email=contact_email, contact_type="seller" if data.get("listing_type") == "sale" else "landlord", source="screenshot_capture", created_by=user.id)
            db.add(contact)
            db.flush()
        if not db.query(ContactProperty).filter(ContactProperty.contact_id == contact.id, ContactProperty.property_id == prop.id).first():
            db.add(ContactProperty(contact_id=contact.id, property_id=prop.id))

    recompute_score(db, prop)
    qualification = qualify_listing(prop)
    opportunity = db.query(DiscoveryOpportunity).filter(DiscoveryOpportunity.property_id == prop.id).first()
    if opportunity is None:
        opportunity = DiscoveryOpportunity(property_id=prop.id, classification=qualification.classification, qualification_status=qualification.status, qualification_reason=qualification.reason, discovery_score=qualification.score)
        db.add(opportunity)
        db.flush()
    else:
        opportunity.classification = qualification.classification
        opportunity.qualification_status = qualification.status
        opportunity.qualification_reason = qualification.reason
        opportunity.discovery_score = qualification.score
        recompute_opportunity_intelligence(db, opportunity)

    source = db.query(Source).filter(Source.source_key == "screenshot_capture").first()
    if source is None:
        source = Source(name="Capture Listing", source_key="screenshot_capture", collector_type="manual_capture", environment="development", is_enabled=True)
        db.add(source)
        db.flush()
    observation = ListingObservation(
        source_id=source.id,
        property_id=prop.id,
        source_listing_id=f"capture:{capture.id}",
        canonical_url=data.get("source_url"),
        source_type="capture",
        discovery_method="manual_capture",
        source_confidence="medium",
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
            contact_agency=data.get("agency_name"),
        contact_confidence="medium" if (contact_name or contact_phone or contact_email) else "unknown",
        lifecycle_status="new",
        raw_payload=json.dumps(data),
    )
    db.add(observation)
    db.flush()
    opportunity.latest_observation_id = observation.id

    if opportunity.qualification_status != "qualified":
        opportunity.qualification_status = "qualified"
        opportunity.qualification_reason = qualification.reason or "Qualified from reviewed capture intake."
        opportunity.reviewed_by = user.id
        opportunity.reviewed_at = datetime.now(timezone.utc)
        recompute_opportunity_intelligence(db, opportunity)

    if opportunity.qualification_status == "qualified" and opportunity.classification in {"seller", "landlord"} and contact is not None:
        promotion = promote_qualified_opportunity(db, user, opportunity, create_task=True, payload=None)
        capture.extracted_data = {**data, **metadata, "_extraction_status": "reviewed"}
        capture.property_id = prop.id
        capture.contact_id = contact.id
        capture.opportunity_id = opportunity.id
        capture.status = "saved"
        db.commit()
        db.refresh(capture)
        return _serialize_capture(db, capture)

    capture.extracted_data = {**data, **metadata, "_extraction_status": "reviewed"}
    capture.property_id = prop.id
    capture.contact_id = contact.id if contact else None
    capture.opportunity_id = opportunity.id
    capture.status = "saved"
    db.commit()
    db.refresh(capture)
    return _serialize_capture(db, capture)


@router.post("/{capture_id}/decline", response_model=CaptureOut)
def decline_capture(capture_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    capture = db.query(Capture).filter(Capture.id == capture_id, Capture.user_id == user.id).first()
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    if capture.property_id or capture.opportunity_id:
        raise HTTPException(status_code=409, detail="Saved opportunities cannot be declined from the capture review")
    capture.status = "declined"
    capture.extraction_notes = "Declined during manual review. Original evidence retained."
    db.commit()
    db.refresh(capture)
    return _serialize_capture(db, capture)


@router.delete("/{capture_id}", status_code=204)
def delete_capture(capture_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    capture = db.query(Capture).filter(Capture.id == capture_id, Capture.user_id == user.id).first()
    if capture is None: raise HTTPException(status_code=404, detail="Capture not found")
    if capture.property_id or capture.opportunity_id: raise HTTPException(status_code=409, detail="Saved captures cannot be deleted from the evidence workflow")
    remove_object(capture.object_key or capture.storage_path, capture.storage_provider, capture.storage_bucket)
    db.delete(capture)
    db.commit()