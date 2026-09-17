import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.communication import CommunicationAccount, CommunicationMessage, Conversation
from app.models.contact import Contact
from app.models.user import User
from app.schemas.communication import CommunicationAccountOut, ConversationOut, MessageOut, MessageReadUpdate, NormalizedMessageInput
from app.services.communication_provider import MockEmailProvider, NormalizedAttachment, NormalizedMessage
from app.services.communication_service import CommunicationService
from app.services.authorization import can_access_entity
from app.core.config import settings

router = APIRouter()


def _message_from_input(payload: NormalizedMessageInput) -> NormalizedMessage:
    return NormalizedMessage(
        provider="mock_email", account_identifier=payload.account_identifier,
        external_message_id=payload.external_message_id, external_thread_id=payload.external_thread_id,
        channel=payload.channel, direction=payload.direction, sender_name=payload.sender_name,
        sender_address=payload.sender_address, recipients=payload.recipients, subject=payload.subject,
        body=payload.body, timestamp=payload.timestamp, contact_id=payload.contact_id,
        lead_id=payload.lead_id, property_id=payload.property_id,
        attachments=[NormalizedAttachment(**attachment.model_dump()) for attachment in payload.attachments], metadata=payload.metadata,
    )


@router.get("/accounts", response_model=list[CommunicationAccountOut])
def list_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(CommunicationAccount).filter(CommunicationAccount.user_id == user.id).order_by(CommunicationAccount.created_at.desc()).all()


@router.get("/providers")
def provider_status(_user: User = Depends(get_current_user)):
    """Expose provider readiness without returning credentials or secrets."""
    return {
        "telephony": {"status": "configured" if settings.VOIP_PROVIDER else "not_configured", "provider": settings.VOIP_PROVIDER},
        "email": {"status": "configured" if settings.EMAIL_PROVIDER else "not_configured", "provider": settings.EMAIL_PROVIDER},
        "whatsapp": {"status": "configured" if settings.WHATSAPP_PROVIDER else "not_configured", "provider": settings.WHATSAPP_PROVIDER},
        "sms": {"status": "configured" if settings.SMS_PROVIDER else "not_configured", "provider": settings.SMS_PROVIDER},
    }


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    channel: str | None = None,
    unread: bool = False,
    lead_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Conversation).filter(Conversation.user_id == user.id)
    if channel: query = query.filter(Conversation.channel == channel)
    if unread: query = query.filter(Conversation.unread_count > 0)
    if lead_id: query = query.filter(Conversation.lead_id == lead_id)
    if contact_id: query = query.filter(Conversation.contact_id == contact_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.outerjoin(Contact, Conversation.contact_id == Contact.id).filter(
            or_(Conversation.subject.ilike(term), Contact.name.ilike(term), Contact.phone.ilike(term), Contact.email.ilike(term))
        )
    return query.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc()).all()


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not item: raise HTTPException(status_code=404, detail="Conversation not found")
    return item


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    return db.query(CommunicationMessage).filter(CommunicationMessage.conversation_id == conversation.id).order_by(CommunicationMessage.created_at.asc()).all()


@router.post("/messages", response_model=MessageOut, status_code=201)
def create_mock_message(payload: NormalizedMessageInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # This is intentionally a mock/test ingress. It never contacts an external provider.
    for entity_type, entity_id in (("contact", payload.contact_id), ("lead", payload.lead_id), ("listing", payload.property_id)):
        if entity_id is not None and not can_access_entity(db, entity_type, entity_id, user):
            raise HTTPException(status_code=404, detail=f"{entity_type.title()} not found")
    normalized = _message_from_input(payload)
    if normalized.direction == "outbound" and normalized.channel == "email":
        normalized = MockEmailProvider().send_message(normalized)
        normalized.metadata["provider_confirmed"] = True
    elif normalized.direction == "outbound":
        normalized.metadata["provider_confirmed"] = False
    try:
        return CommunicationService(db, user.id).ingest_message(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/messages/{message_id}/read", response_model=MessageOut)
def update_read_state(message_id: uuid.UUID, payload: MessageReadUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = db.query(CommunicationMessage).join(Conversation).filter(
        CommunicationMessage.id == message_id, Conversation.user_id == user.id,
    ).first()
    if not message: raise HTTPException(status_code=404, detail="Message not found")
    if payload.is_read:
        return CommunicationService(db, user.id).mark_read(message)
    message.is_read = False
    db.commit(); db.refresh(message)
    return message
