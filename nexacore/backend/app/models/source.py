import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Source(Base):
    """A data source a collector can pull from. Sources start disabled unless
    they're a confirmed-approved integration (see Source Management docs)."""
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    collector_type: Mapped[str] = mapped_column(String(100), nullable=False)  # matches CollectorRegistry key
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    config: Mapped[str | None] = mapped_column(Text)  # JSON string of collector-specific config

    last_successful_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    listings_collected_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
