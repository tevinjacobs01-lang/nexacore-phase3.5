import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# NexaCore Realty Intelligence pipeline
LEAD_PIPELINE_STAGES = [
    "new",
    "researching",
    "contacted",
    "responded",
    "qualified",
    "follow_up",
    "appointment",
    "listing_opportunity",
    "mandate_agreement",
    "won",
    "lost",
]


# Backwards compatibility with older NexaCore stages
LEGACY_STATUS_MAP = {
    "converted": "won",
    "not_interested": "lost",
    "closed": "lost",
}


def resolve_stage(status: str) -> str:
    return LEGACY_STATUS_MAP.get(status, status)


# Lead categories
LEAD_TYPES = [
    "seller",
    "landlord",
    "buyer",
    "tenant",
    "investor",
]


# Lead sources
LEAD_SOURCES = [
    "website",
    "facebook",
    "instagram",
    "property_portal",
    "referral",
    "manual",
    "discovery",
]


class Lead(Base):
    """
    NexaCore Realty Intelligence Lead.

    Contact is always required.
    Property is optional because buyers and tenants
    may not have a property yet.
    """

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id"),
        nullable=False,
    )

    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id"),
        nullable=True,
    )

    lead_type: Mapped[str] = mapped_column(
        String(30),
        default="seller",
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        default="manual",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="new",
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
    )

    lead_score: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )

    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    next_follow_up: Mapped[date | None] = mapped_column(
        Date
    )

    notes: Mapped[str | None] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
