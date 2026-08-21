import uuid
from datetime import date, datetime
from pydantic import BaseModel


class PropertyBase(BaseModel):
    listing_reference: str | None = None
    address: str | None = None
    suburb: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    listing_type: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    garages: int | None = None
    floor_size_sqm: float | None = None
    stand_size_sqm: float | None = None
    asking_price: float | None = None
    monthly_rental: float | None = None
    listing_date: date | None = None
    days_on_market: int | None = None
    listing_source: str | None = None
    listing_url: str | None = None
    agent_name: str | None = None
    contact_number: str | None = None
    email: str | None = None
    notes: str | None = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(PropertyBase):
    contact_status: str | None = None
    follow_up_date: date | None = None


class PropertyOut(PropertyBase):
    id: uuid.UUID
    contact_status: str
    lead_score: int
    follow_up_date: date | None
    last_contacted_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
