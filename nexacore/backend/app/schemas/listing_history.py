import uuid
from datetime import datetime
from pydantic import BaseModel


class ListingHistoryOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    previous_price: float | None
    new_price: float | None
    previous_description: str | None
    new_description: str | None
    previous_status: str | None
    new_status: str | None
    changed_at: datetime

    class Config:
        from_attributes = True


VALID_LISTING_STATUSES = {
    "new", "active", "contacted", "responded", "follow_up", "appointment",
    "converted", "not_interested", "closed", "expired", "unknown",
}


class StatusChangeRequest(BaseModel):
    status: str
