import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

CONTACT_TYPES = {
    "property_owner", "buyer", "tenant", "landlord", "seller", "agent", "other",
}
PREFERRED_CONTACT_METHODS = {"phone", "email", "sms", "whatsapp", "any"}


class Contact(Base):
    """Normalized contact record (agent, seller, buyer, tenant, etc.),
    reusable across listings and the lead pipeline. Kept separate from
    Property so a single person isn't duplicated per listing."""
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)

    # Sprint 21 additions
    preferred_contact_method: Mapped[str | None] = mapped_column(String(20))  # phone|email|sms|whatsapp|any
    contact_type: Mapped[str | None] = mapped_column(String(30))  # see CONTACT_TYPES
    source: Mapped[str | None] = mapped_column(String(255))  # where this contact came from
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
