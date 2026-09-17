from datetime import datetime
from pydantic import BaseModel, Field


class WebhookMessage(BaseModel):
    external_message_id: str
    external_thread_id: str | None = None
    account_identifier: str
    channel: str = Field(pattern="^(email|whatsapp|sms|voip)$")
    sender_name: str | None = None
    sender_address: str
    recipients: list[str] = Field(default_factory=list)
    subject: str | None = None
    body: str = ""
    timestamp: datetime | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    property_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ProviderWebhookPayload(BaseModel):
    event_id: str
    provider: str
    message: WebhookMessage


class ListingFeedWebhookPayload(BaseModel):
    event_id: str
    provider: str
    source_key: str
    account_identifier: str
    listing: dict