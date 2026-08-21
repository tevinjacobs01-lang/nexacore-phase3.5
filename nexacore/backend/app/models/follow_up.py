import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

FOLLOW_UP_TYPES = {"call", "message", "email", "meeting", "general"}
FOLLOW_UP_STATUSES = {"pending", "completed", "cancelled"}
# "overdue" is derived (pending + due_at in the past), not stored


class FollowUp(Base):
    """A scheduled follow-up (Sprint 25) — distinct from Task in that every
    follow-up implies "this lead needs another touch," and overdue ones are
    surfaced dashboard-wide so a lead never silently drops out of the pipeline."""
    __tablename__ = "follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))

    follow_up_type: Mapped[str] = mapped_column(String(20), nullable=False)  # see FOLLOW_UP_TYPES
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # see FOLLOW_UP_STATUSES
    notes: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
