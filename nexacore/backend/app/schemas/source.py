import uuid
from datetime import datetime
from pydantic import BaseModel


class SourceOut(BaseModel):
    id: uuid.UUID
    name: str
    source_key: str
    collector_type: str
    is_enabled: bool
    disabled_reason: str | None
    last_successful_scan_at: datetime | None
    last_error: str | None
    listings_collected_count: int

    class Config:
        from_attributes = True


class SourceUpdate(BaseModel):
    is_enabled: bool | None = None
    disabled_reason: str | None = None
    config: str | None = None
