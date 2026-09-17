import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SavedSearch(Base):
    """User-owned discovery criteria for future matching and alerts."""

    __tablename__ = "saved_searches"
    __table_args__ = (CheckConstraint("lead_type IN ('seller', 'landlord')", name="ck_saved_search_lead_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    suburbs: Mapped[str | None] = mapped_column(Text)
    property_type: Mapped[str | None] = mapped_column(String(100))
    min_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    max_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    listing_type: Mapped[str | None] = mapped_column(String(20))
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    minimum_score: Mapped[int | None] = mapped_column(Integer)
    lead_type: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")