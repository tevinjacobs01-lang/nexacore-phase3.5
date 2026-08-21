import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

INTERACTION_TYPES = {"call", "email", "meeting", "message", "note", "status_change"}
INTERACTION_DIRECTIONS = {"outgoing", "incoming", "internal"}


class Interaction(Base):
    """A single entry in a contact/lead's chronological activity timeline
    (Sprint 22): a call, email, meeting, message, note, or status change."""
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    interaction_type: Mapped[str] = mapped_column(String(30), nullable=False)  # see INTERACTION_TYPES
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # see INTERACTION_DIRECTIONS
    outcome: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
