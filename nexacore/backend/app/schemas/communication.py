import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AttachmentMetadata(BaseModel):
    provider_attachment_id: str | None = None
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    storage_key: str | None = None
    external_url: str | None = None


class NormalizedMessageInput(BaseModel):
    """Credential-free normalized payload used by the mock/test adapter."""
    account_identifier: str = "mock-email"
    external_message_id: str | None = None
    external_thread_id: str | None = None
    channel: str = "email"
    direction: str = "outbound"
    sender_name: str | None = None
    sender_address: str | None = None
    recipients: list[str] = Field(default_factory=list)
    subject: str | None = None
    body: str = ""
    timestamp: datetime | None = None
    contact_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    attachments: list[AttachmentMetadata] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class CommunicationAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    provider: str
    account_type: str
    display_name: str | None
    external_identifier: str | None
    status: str
    sync_enabled: bool
    last_synced_at: datetime | None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contact_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    property_id: uuid.UUID | None
    communication_account_id: uuid.UUID | None
    channel: str
    external_thread_id: str | None
    subject: str | None
    status: str
    last_message_at: datetime | None
    unread_count: int
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    conversation_id: uuid.UUID
    communication_account_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    property_id: uuid.UUID | None
    direction: str
    channel: str
    provider_message_id: str | None
    provider_thread_id: str | None
    sender_name: str | None
    sender_address: str | None
    recipient_address: str | None
    subject: str | None
    body_text: str | None
    body_preview: str | None
    received_at: datetime | None
    sent_at: datetime | None
    status: str
    is_read: bool
    has_attachments: bool
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime


class MessageReadUpdate(BaseModel):
    is_read: bool = True
