import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeadScoreRule(Base):
    """A single configurable scoring rule, editable from admin settings."""
    __tablename__ = "lead_score_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g. "days_on_market_gt_30", "preferred_suburb", "price_range_match"
    rule_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Free-form JSON-ish config stored as text (e.g. threshold values, suburb list)
    config: Mapped[str | None] = mapped_column(String(2000))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PropertyScoreHistory(Base):
    """Snapshot of a property's score at a point in time, for trend/audit purposes."""
    __tablename__ = "property_score_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    breakdown: Mapped[str | None] = mapped_column(String(2000))  # JSON string of rule_key -> points
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
