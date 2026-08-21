import uuid
from datetime import date, datetime
from pydantic import BaseModel

ACTIVITY_TYPES = {
    "contacted", "interested", "not_interested", "note",
    "follow_up_scheduled", "archived",
}


class ActivityCreate(BaseModel):
    activity_type: str
    note: str | None = None
    follow_up_date: date | None = None  # only used when activity_type == follow_up_scheduled


class ActivityOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    user_id: uuid.UUID | None
    activity_type: str
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True
