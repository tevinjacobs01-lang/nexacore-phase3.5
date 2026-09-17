import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ListingObservation(Base):
    """A source-specific observation of a property listing."""

    __tablename__ = "listing_observations"
    __table_args__ = (
        UniqueConstraint("source_id", "source_listing_id", name="uq_observation_source_listing"),
        CheckConstraint("lifecycle_status IN ('new', 'active', 'price_changed', 'removed', 'expired', 'relisted')", name="ck_observation_lifecycle_status"),
        CheckConstraint("source_confidence IN ('high', 'medium', 'low', 'unknown')", name="ck_observation_source_confidence"),
        CheckConstraint("contact_confidence IN ('high', 'medium', 'low', 'unknown')", name="ck_observation_contact_confidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    source_listing_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)
    source_type: Mapped[str | None] = mapped_column(String(50))
    discovery_method: Mapped[str | None] = mapped_column(String(100))
    source_confidence: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_company: Mapped[str | None] = mapped_column(String(255))
    contact_agency: Mapped[str | None] = mapped_column(String(255))
    contact_confidence: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="new", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[str | None] = mapped_column(Text)

    source = relationship("Source")
    property = relationship("Property")