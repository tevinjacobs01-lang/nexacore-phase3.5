import uuid
from datetime import datetime
from pydantic import BaseModel


class FollowUpCreate(BaseModel):
    lead_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    follow_up_type: str
    due_at: datetime
    notes: str | None = None


class FollowUpUpdate(BaseModel):
    due_at: datetime | None = None
    status: str | None = None
    notes: str | None = None


class FollowUpOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    follow_up_type: str
    due_at: datetime
    status: str
    notes: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True
