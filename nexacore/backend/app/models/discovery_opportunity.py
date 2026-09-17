import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DiscoveryOpportunity(Base):
    """Reviewable discovery record kept separate from CRM leads."""

    __tablename__ = "discovery_opportunities"
    __table_args__ = (
        CheckConstraint("classification IN ('seller', 'landlord', 'unknown')", name="ck_opportunity_classification"),
        CheckConstraint("qualification_status IN ('unreviewed', 'qualified', 'not_qualified', 'review_required')", name="ck_opportunity_qualification_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True, unique=True)
    latest_observation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("listing_observations.id"), index=True)
    classification: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    qualification_status: Mapped[str] = mapped_column(String(30), default="unreviewed", nullable=False)
    qualification_reason: Mapped[str | None] = mapped_column(Text)
    discovery_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_confidence: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    intelligence_reasons: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(String(255))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    property = relationship("Property")
    latest_observation = relationship("ListingObservation", foreign_keys=[latest_observation_id])