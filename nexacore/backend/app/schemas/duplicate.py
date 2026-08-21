import uuid
from datetime import datetime
from pydantic import BaseModel


class DuplicateMatchOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    matched_property_id: uuid.UUID
    match_type: str
    match_reason: str
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True
