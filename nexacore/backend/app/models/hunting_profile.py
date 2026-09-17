import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HuntingProfile(Base):
    """Configurable prioritization profile; it never acts as an ingestion gate."""
    __tablename__ = "hunting_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), default="Default property lead profile", nullable=False)
    target_locations: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    property_types: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    intent_types: Mapped[str] = mapped_column(Text, default="[\"sale\", \"rent\"]", nullable=False)
    advertiser_types: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    priority_signals: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    minimum_display_confidence: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)