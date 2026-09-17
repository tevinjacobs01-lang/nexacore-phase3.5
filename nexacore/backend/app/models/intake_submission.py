import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IntakeSubmission(Base):
    """Small audit record for a user-provided URL, text, or existing Capture."""

    __tablename__ = "intake_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    input_type: Mapped[str] = mapped_column(String(20), nullable=False)  # url | text | screenshot
    raw_input: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000), index=True)
    source_domain: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="review_required")
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    property_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), index=True)
    capture_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("captures.id"), index=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("discovery_opportunities.id"), index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
