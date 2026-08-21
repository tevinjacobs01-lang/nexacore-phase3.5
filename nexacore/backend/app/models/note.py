import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# "deal" is intentionally NOT included here. The original spec (Sprint 23)
# lists notes as attachable to "listings, contacts, leads, or deals," but no
# Deal model exists anywhere in this codebase (Phases 1-3 never introduced
# one). Rather than silently accepting entity_type="deal" with zero
# existence validation (inconsistent with listing/contact/lead, which are
# validated against real tables), requests for "deal" are rejected with a
# clear 400 until a Deal model is deliberately added. See
# docs/DEAL_ENTITY_DECISION.md for the full reasoning.
NOTE_ENTITY_TYPES = {"listing", "contact", "lead"}


class Note(Base):
    """A note attached to a listing, contact, lead, or deal (Sprint 23).
    Polymorphic via (entity_type, entity_id) rather than one FK column per
    entity type, so adding a new notable entity later needs no schema change."""
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # see NOTE_ENTITY_TYPES
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
