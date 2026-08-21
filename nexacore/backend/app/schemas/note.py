import uuid
from datetime import datetime
from pydantic import BaseModel


class NoteCreate(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    content: str
    is_private: bool = False


class NoteOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    content: str
    is_private: bool
    author_id: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True
