import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TEMPLATE_TYPES = {
    "initial_seller_contact", "follow_up", "appointment_confirmation",
    "appointment_reminder", "buyer_enquiry", "rental_enquiry", "general_response",
}

TEMPLATE_VARIABLES = [
    "contact_name", "property_address", "property_price", "agent_name",
    "suburb", "listing_url",
]


class CommunicationTemplate(Base):
    """A reusable message template (Sprint 29) with {{variable}} placeholders.
    Rendering only ever produces text for the agent to review and send
    manually — see app/services/templates.py. No sending integration here."""
    __tablename__ = "communication_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # see TEMPLATE_TYPES
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
