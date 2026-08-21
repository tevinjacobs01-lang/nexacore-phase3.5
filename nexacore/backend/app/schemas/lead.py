import uuid
from datetime import date, datetime
from pydantic import BaseModel

from app.models.lead import LEAD_PIPELINE_STAGES

LEAD_STATUSES = set(LEAD_PIPELINE_STAGES)
LEAD_PRIORITIES = {"low", "medium", "high"}


class LeadCreate(BaseModel):
    property_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    priority: str = "medium"
    notes: str | None = None


class LeadUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_agent_id: uuid.UUID | None = None
    next_follow_up: date | None = None
    notes: str | None = None


class LeadOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    contact_id: uuid.UUID | None
    status: str
    priority: str
    assigned_agent_id: uuid.UUID | None
    last_contacted_at: datetime | None
    next_follow_up: date | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AssignLeadRequest(BaseModel):
    agent_id: uuid.UUID
