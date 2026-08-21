import uuid
from datetime import datetime
from pydantic import BaseModel


class ScanJobOut(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    listings_discovered: int
    new_listings: int
    updated_listings: int
    duplicate_listings: int
    error_count: int
    errors: str | None

    class Config:
        from_attributes = True
