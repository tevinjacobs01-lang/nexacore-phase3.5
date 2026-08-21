import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Assignment(Base):
    """Full assignment history for a Lead (Sprint 28). `Lead.assigned_agent_id`
    (from Phase 2) remains the fast-access "current owner" pointer; this
    table is the append-only audit trail behind it — every reassignment
    adds a row rather than overwriting one, and exactly one row per lead
    has is_current=True at a time."""
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
