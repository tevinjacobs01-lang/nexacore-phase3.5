import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

APPOINTMENT_STATUSES = {"scheduled", "confirmed", "completed", "cancelled", "no_show", "rescheduled"}
APPOINTMENT_TYPES = {"viewing", "listing_presentation", "signing", "consultation", "other"}


class Appointment(Base):
    """A scheduled appointment (Sprint 26). `starts_at` combines date+time;
    architecture leaves room for a future calendar sync (e.g. an
    `external_calendar_event_id` column) without a breaking change."""
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    location: Mapped[str | None] = mapped_column(String(500))
    appointment_type: Mapped[str] = mapped_column(String(30), default="viewing")  # see APPOINTMENT_TYPES
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # see APPOINTMENT_STATUSES

    # Reserved for future calendar sync (Sprint 26 note: "prepare the
    # architecture for future calendar integrations") — unused for now.
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
