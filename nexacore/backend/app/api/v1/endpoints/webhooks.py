import hashlib
import hmac
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.communication import CommunicationAccount
from app.models.source import Source
from app.models.webhook_event import WebhookEvent
from app.schemas.webhook import ListingFeedWebhookPayload, ProviderWebhookPayload
from app.services.communication_provider import NormalizedMessage
from app.services.communication_service import CommunicationService
from app.services.ingestion import ingest_listing
from app.services.property_intent import detect_property_intent
from app.services.normalization import normalize_phone

router = APIRouter()


def _valid_signature(payload: bytes, signature: str | None) -> bool:
    if not settings.WEBHOOK_SIGNING_SECRET or not signature:
        return False
    expected = hmac.new(settings.WEBHOOK_SIGNING_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


@router.post("/provider", status_code=status.HTTP_202_ACCEPTED)
async def receive_provider_webhook(
    payload: ProviderWebhookPayload,
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    raw_payload = await request.body()
    if not _valid_signature(raw_payload, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        account = db.query(CommunicationAccount).filter(
            CommunicationAccount.provider == payload.provider,
            CommunicationAccount.external_identifier == payload.message.account_identifier,
        ).first()
        if account is None:
            raise HTTPException(status_code=404, detail="Communication account not found")

        event = WebhookEvent(
            provider=payload.provider,
            external_event_id=payload.event_id,
            account_identifier=payload.message.account_identifier,
            payload=payload.model_dump(),
        )
        db.add(event)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return {"status": "duplicate", "event_id": payload.event_id}

        message = payload.message
        normalized = NormalizedMessage(
            provider=payload.provider,
            account_identifier=message.account_identifier,
            external_message_id=message.external_message_id,
            external_thread_id=message.external_thread_id,
            channel=message.channel,
            direction="inbound",
            sender_name=message.sender_name,
            sender_address=message.sender_address,
            recipients=message.recipients,
            subject=message.subject,
            body=message.body,
            timestamp=message.timestamp,
            metadata=message.metadata,
        )
        CommunicationService(db, account.user_id).ingest_message(normalized)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "processed", "event_id": payload.event_id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        event = db.query(WebhookEvent).filter(
            WebhookEvent.provider == payload.provider,
            WebhookEvent.external_event_id == payload.event_id,
        ).first()
        if event:
            event.status = "failed"
            event.error = str(exc)
            db.commit()
        raise HTTPException(status_code=502, detail=f"Webhook processing failed: {exc}") from exc


@router.post("/listing-feed", status_code=status.HTTP_202_ACCEPTED)
async def receive_listing_feed_webhook(
    payload: ListingFeedWebhookPayload,
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Receive one authorised listing update and send it through canonical ingestion.

    Providers must send a unique event_id and an HMAC signature. This endpoint
    is for documented provider/brokerage integrations, not portal scraping.
    """
    raw_payload = await request.body()
    if not _valid_signature(raw_payload, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    source = db.query(Source).filter(Source.source_key == payload.source_key).first()
    if source is None:
        raise HTTPException(status_code=404, detail="Listing source not found")
    if not source.is_enabled:
        raise HTTPException(status_code=409, detail="Listing source is disabled")

    existing = db.query(WebhookEvent).filter(
        WebhookEvent.provider == payload.provider,
        WebhookEvent.external_event_id == payload.event_id,
    ).first()
    if existing:
        return {"status": "duplicate", "event_id": payload.event_id}

    event = WebhookEvent(
        provider=payload.provider,
        external_event_id=payload.event_id,
        account_identifier=payload.account_identifier,
        payload=payload.model_dump(),
    )
    db.add(event)
    try:
        db.flush()
        listing = dict(payload.listing)
        content = listing.get("text") or listing.get("content") or listing.get("description") or listing.get("notes")
        intent = detect_property_intent(content, listing)
        if intent.listing_type and not listing.get("listing_type"):
            listing["listing_type"] = intent.listing_type
        if intent.advertiser_type != "unknown" and not listing.get("seller_type"):
            listing["seller_type"] = intent.advertiser_type
        if content and not listing.get("notes"):
            listing["notes"] = content
        if content and not listing.get("contact_number"):
            phone_match = re.search(r"(?<!\d)(0\d[\d\s-]{8,}\d)(?!\d)", content)
            if phone_match:
                listing["contact_number"] = normalize_phone(phone_match.group(1))
        result = ingest_listing(
            db,
            listing,
            source=source.source_key,
            source_id=source.id,
            source_metadata={
                "source_type": "social" if listing.get("platform") else "webhook",
                "discovery_method": "authorised_social_api" if listing.get("platform") else "authorised_listing_feed_webhook",
                "property_intent": intent.is_property_intent,
                "advertiser_type": intent.advertiser_type,
            },
        )
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "status": "processed",
            "event_id": payload.event_id,
            "outcome": result.outcome,
            "property_id": str(result.property_id) if result.property_id else None,
        }
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate", "event_id": payload.event_id}
    except Exception as exc:
        db.rollback()
        event = db.query(WebhookEvent).filter(
            WebhookEvent.provider == payload.provider,
            WebhookEvent.external_event_id == payload.event_id,
        ).first()
        if event:
            event.status = "failed"
            event.error = str(exc)
            db.commit()
        raise HTTPException(status_code=422, detail=f"Listing feed processing failed: {exc}") from exc