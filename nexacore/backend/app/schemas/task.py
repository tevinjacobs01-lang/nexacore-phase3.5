import uuid
from datetime import date, datetime
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assigned_user_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    due_date: date | None = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_user_id: uuid.UUID | None = None
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    assigned_user_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    due_date: date | None
    priority: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True
