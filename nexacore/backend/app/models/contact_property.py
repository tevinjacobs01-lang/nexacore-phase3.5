import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContactProperty(Base):
    """Many-to-many link: a contact can be associated with multiple listings
    (e.g. a buyer interested in several properties), independent of the lead
    pipeline (Lead is a specific actionable opportunity; this is a looser
    association)."""
    __tablename__ = "contact_properties"
    __table_args__ = (UniqueConstraint("contact_id", "property_id", name="uq_contact_property"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
