import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Sprint 27 — full sales pipeline. This supersedes the simpler 8-stage set
# from Phase 2 (new/contacted/responded/follow_up/appointment/converted/
# not_interested/closed). Existing rows written under the old stage names
# still work at the DB level (status is just a string column) — use
# LEGACY_STATUS_MAP to migrate/interpret them under the new pipeline.
LEAD_PIPELINE_STAGES = [
    "new", "researching", "contacted", "responded", "qualified",
    "follow_up", "appointment", "listing_opportunity", "mandate_agreement",
    "won", "lost",
]

# Maps Phase 2 stage names to their closest Sprint 27 equivalent, so old
# data (or API clients still sending old values) keeps working.
LEGACY_STATUS_MAP = {
    "converted": "won",
    "not_interested": "lost",
    "closed": "lost",
}


def resolve_stage(status: str) -> str:
    """Returns the Sprint 27 stage for a given status string, translating
    legacy Phase 2 values if needed. Unknown values pass through unchanged."""
    return LEGACY_STATUS_MAP.get(status, status)


class Lead(Base):
    """An actionable lead derived from a Listing (Property) + Contact pair."""
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))

    status: Mapped[str] = mapped_column(String(30), default="new")
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low | medium | high
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_follow_up: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
