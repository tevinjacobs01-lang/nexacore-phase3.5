"""Provider-agnostic ingestion and matching service."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.communication import CommunicationAccount, CommunicationAttachment, CommunicationMessage, Conversation
from app.models.contact import Contact
from app.models.interaction import Interaction
from app.models.lead import Lead
from app.models.property import Property
from app.services.communication_provider import NormalizedMessage
from app.services.normalization import normalize_email, normalize_phone


class CommunicationService:
    def __init__(self, db: Session, user_id):
        self.db = db
        self.user_id = user_id

    def _account_for(self, message: NormalizedMessage) -> CommunicationAccount:
        account = self.db.query(CommunicationAccount).filter(
            CommunicationAccount.user_id == self.user_id,
            CommunicationAccount.provider == message.provider,
            CommunicationAccount.external_identifier == message.account_identifier,
        ).first()
        if not account:
            account = CommunicationAccount(
                user_id=self.user_id, provider=message.provider, account_type=message.channel,
                display_name="Mock Email" if message.provider == "mock_email" else message.provider,
                external_identifier=message.account_identifier, status="active", sync_enabled=False,
            )
            self.db.add(account)
            self.db.flush()
        return account

    def match_message(self, message: NormalizedMessage):
        """Link existing CRM data only; messages never manufacture a Lead or marketing record."""
        contact = self.db.get(Contact, message.contact_id) if message.contact_id else None
        address = message.sender_address if message.direction == "inbound" else (message.recipients[0] if message.recipients else None)
        if not contact and address:
            normalized_email = normalize_email(address)
            normalized_phone = normalize_phone(address)
            if message.channel in {"sms", "whatsapp", "voip", "phone"}:
                contact = self.db.query(Contact).filter(Contact.phone == normalized_phone).first()
            if not contact and normalized_email:
                contact = self.db.query(Contact).filter(Contact.email == normalized_email).first()
        lead = self.db.get(Lead, message.lead_id) if message.lead_id else None
        if not lead and contact:
            lead = self.db.query(Lead).filter(Lead.contact_id == contact.id).order_by(Lead.created_at.desc()).first()
        prop = self.db.get(Property, message.property_id) if message.property_id else None
        if not prop and lead and lead.property_id:
            prop = self.db.get(Property, lead.property_id)
        return contact, lead, prop

    def create_or_update_conversation(self, account: CommunicationAccount, message: NormalizedMessage, contact, lead, prop) -> Conversation:
        conversation = None
        if message.external_thread_id:
            conversation = self.db.query(Conversation).filter(
                Conversation.user_id == self.user_id,
                Conversation.communication_account_id == account.id,
                Conversation.external_thread_id == message.external_thread_id,
            ).first()
        if not conversation and contact:
            conversation = self.db.query(Conversation).filter(
                Conversation.user_id == self.user_id,
                Conversation.contact_id == contact.id,
                Conversation.external_thread_id.is_(None),
            ).order_by(Conversation.updated_at.desc()).first()
        if not conversation:
            conversation = Conversation(
                user_id=self.user_id, communication_account_id=account.id, channel=message.channel,
                external_thread_id=message.external_thread_id, subject=message.subject,
                contact_id=contact.id if contact else None, lead_id=lead.id if lead else None,
                property_id=prop.id if prop else None,
            )
            self.db.add(conversation)
            self.db.flush()
        else:
            conversation.contact_id = conversation.contact_id or (contact.id if contact else None)
            conversation.lead_id = conversation.lead_id or (lead.id if lead else None)
            conversation.property_id = conversation.property_id or (prop.id if prop else None)
            conversation.subject = conversation.subject or message.subject
        return conversation

    def record_timeline_event(self, message: CommunicationMessage):
        direction = "incoming" if message.direction == "inbound" else "outgoing"
        preview = message.body_preview or message.subject or "Email message"
        if message.contact_id or message.lead_id:
            self.db.add(Interaction(
                contact_id=message.contact_id, lead_id=message.lead_id, user_id=self.user_id,
                interaction_type="email", direction=direction, outcome=message.subject, notes=preview,
                occurred_at=message.received_at or message.sent_at or datetime.now(timezone.utc),
            ))
        if message.property_id:
            self.db.add(Activity(property_id=message.property_id, user_id=self.user_id, activity_type="email", note=preview))

    def ingest_message(self, message: NormalizedMessage) -> CommunicationMessage:
        if message.channel not in {"email", "whatsapp", "sms", "voip", "website", "other"}:
            raise ValueError("Unsupported communication channel")
        if message.direction not in {"inbound", "outbound"}:
            raise ValueError("direction must be inbound or outbound")
        account = self._account_for(message)
        if message.external_message_id:
            existing = self.db.query(CommunicationMessage).filter(
                CommunicationMessage.communication_account_id == account.id,
                CommunicationMessage.provider_message_id == message.external_message_id,
            ).first()
            if existing:
                return existing
        contact, lead, prop = self.match_message(message)
        conversation = self.create_or_update_conversation(account, message, contact, lead, prop)
        timestamp = message.timestamp or datetime.now(timezone.utc)
        communication = CommunicationMessage(
            conversation_id=conversation.id, communication_account_id=account.id,
            contact_id=contact.id if contact else None, lead_id=lead.id if lead else None, property_id=prop.id if prop else None,
            direction=message.direction, channel=message.channel, provider_message_id=message.external_message_id,
            provider_thread_id=message.external_thread_id, sender_name=message.sender_name,
            sender_address=message.sender_address, recipient_address=", ".join(message.recipients) or None,
            subject=message.subject, body_text=message.body, body_preview=message.body[:500],
            received_at=timestamp if message.direction == "inbound" else None,
            sent_at=timestamp if message.direction == "outbound" else None,
            status=(
                "received"
                if message.direction == "inbound"
                else "sent" if message.metadata.get("provider_confirmed") else "queued"
            ),
            is_read=message.direction == "outbound", has_attachments=bool(message.attachments), metadata_=message.metadata,
        )
        self.db.add(communication)
        conversation.last_message_at = timestamp
        if message.direction == "inbound": conversation.unread_count += 1
        self.db.flush()
        for attachment in message.attachments:
            self.db.add(CommunicationAttachment(
                message_id=communication.id, provider_attachment_id=attachment.provider_attachment_id,
                filename=attachment.filename, mime_type=attachment.mime_type, size_bytes=attachment.size_bytes,
                storage_key=attachment.storage_key, external_url=attachment.external_url,
            ))
        self.record_timeline_event(communication)
        self.db.commit()
        self.db.refresh(communication)
        return communication

    def mark_read(self, message: CommunicationMessage):
        if not message.is_read:
            message.is_read = True
            conversation = self.db.get(Conversation, message.conversation_id)
            if conversation and message.direction == "inbound":
                conversation.unread_count = max(0, conversation.unread_count - 1)
            self.db.commit()
            self.db.refresh(message)
        return message
