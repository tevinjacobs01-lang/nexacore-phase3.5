import uuid
from datetime import datetime
from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    original_filename: str
    content_type: str | None
    size_bytes: int
    uploaded_by: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True
