import uuid
from datetime import date, datetime

from sqlalchemy import String, Integer, Numeric, Date, DateTime, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_properties_suburb_city", "suburb", "city"),
        Index("ix_properties_listing_ref", "listing_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_reference: Mapped[str | None] = mapped_column(String(100), index=True)

    address: Mapped[str | None] = mapped_column(String(500))
    suburb: Mapped[str | None] = mapped_column(String(255), index=True)
    city: Mapped[str | None] = mapped_column(String(255), index=True)
    province: Mapped[str | None] = mapped_column(String(255))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))

    listing_type: Mapped[str | None] = mapped_column(String(20))  # "sale" | "rent"
    property_type: Mapped[str | None] = mapped_column(String(100))  # house, apartment, etc.
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    garages: Mapped[int | None] = mapped_column(Integer)
    floor_size_sqm: Mapped[float | None] = mapped_column(Numeric(10, 2))
    stand_size_sqm: Mapped[float | None] = mapped_column(Numeric(10, 2))

    asking_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    monthly_rental: Mapped[float | None] = mapped_column(Numeric(14, 2))

    listing_date: Mapped[date | None] = mapped_column(Date)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    days_on_market: Mapped[int | None] = mapped_column(Integer)

    listing_source: Mapped[str | None] = mapped_column(String(255))
    listing_url: Mapped[str | None] = mapped_column(String(1000))

    agent_name: Mapped[str | None] = mapped_column(String(255))
    contact_number: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))

    notes: Mapped[str | None] = mapped_column(Text)

    # Signals used by the scoring engine
    is_relisted: Mapped[bool] = mapped_column(default=False)
    previous_asking_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    price_reduced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # CRM state (Phase 1 — simple quick-action status, kept for backward compatibility)
    contact_status: Mapped[str] = mapped_column(String(50), default="not_contacted")
    # not_contacted | contacted | interested | not_interested | archived

    # Lead pipeline lifecycle state (Phase 2 — fuller status set used by the
    # scan/lead pipeline; distinct from contact_status above)
    listing_status: Mapped[str] = mapped_column(String(30), default="new")
    # new | active | contacted | responded | follow_up | appointment |
    # converted | not_interested | closed | expired | unknown

    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
