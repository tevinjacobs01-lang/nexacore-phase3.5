import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ListingHistory(Base):
    """Audit trail of meaningful changes to a listing: price, description,
    and status. Used later to spot motivated-seller signals (e.g. repeated
    price drops)."""
    __tablename__ = "listing_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)

    previous_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    new_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    previous_description: Mapped[str | None] = mapped_column(Text)
    new_description: Mapped[str | None] = mapped_column(Text)
    previous_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str | None] = mapped_column(String(50))

    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
