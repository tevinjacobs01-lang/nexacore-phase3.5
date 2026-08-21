import uuid
from datetime import datetime
from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    lead_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    starts_at: datetime
    duration_minutes: int = 30
    location: str | None = None
    appointment_type: str = "viewing"
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    starts_at: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    notes: str | None = None
    status: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    starts_at: datetime
    duration_minutes: int
    location: str | None
    appointment_type: str
    notes: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
