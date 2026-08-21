import uuid
from datetime import datetime
from pydantic import BaseModel


class InteractionCreate(BaseModel):
    contact_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    interaction_type: str
    direction: str
    outcome: str | None = None
    notes: str | None = None


class InteractionOut(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    user_id: uuid.UUID | None
    interaction_type: str
    direction: str
    outcome: str | None
    notes: str | None
    occurred_at: datetime

    class Config:
        from_attributes = True
