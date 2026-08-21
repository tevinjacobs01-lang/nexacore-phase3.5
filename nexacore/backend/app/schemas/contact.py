import uuid
from datetime import datetime
from pydantic import BaseModel


class ContactCreate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_contact_method: str | None = None
    contact_type: str | None = None
    source: str | None = None
    notes: str | None = None
    force_create: bool = False  # bypass duplicate check if the agent confirms it's genuinely new


class ContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_contact_method: str | None = None
    contact_type: str | None = None
    source: str | None = None
    notes: str | None = None


class ContactOut(BaseModel):
    id: uuid.UUID
    name: str | None
    phone: str | None
    email: str | None
    preferred_contact_method: str | None
    contact_type: str | None
    source: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
