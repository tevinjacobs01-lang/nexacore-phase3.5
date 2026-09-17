import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str | None = None
    suburbs: str | None = None
    property_type: str | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    listing_type: str | None = None
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    minimum_score: int | None = Field(default=None, ge=0, le=100)
    lead_type: str
    enabled: bool = True

    @model_validator(mode="after")
    def validate_search(self):
        if self.lead_type not in {"seller", "landlord"}:
            raise ValueError("lead_type must be seller or landlord")
        if self.listing_type is not None and self.listing_type not in {"sale", "rent"}:
            raise ValueError("listing_type must be sale or rent")
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price cannot exceed max_price")
        expected = "sale" if self.lead_type == "seller" else "rent"
        if self.listing_type is not None and self.listing_type != expected:
            raise ValueError(f"{self.lead_type} searches must use listing_type={expected}")
        return self


class SavedSearchUpdate(SavedSearchCreate):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = None
    suburbs: str | None = None
    property_type: str | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    listing_type: str | None = None
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    minimum_score: int | None = Field(default=None, ge=0, le=100)
    lead_type: str | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def validate_partial_fields(self):
        if self.lead_type is not None and self.lead_type not in {"seller", "landlord"}:
            raise ValueError("lead_type must be seller or landlord")
        if self.listing_type is not None and self.listing_type not in {"sale", "rent"}:
            raise ValueError("listing_type must be sale or rent")
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price cannot exceed max_price")
        return self


class SavedSearchOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    location: str | None
    suburbs: str | None
    property_type: str | None
    min_price: float | None
    max_price: float | None
    listing_type: str | None
    bedrooms: int | None
    bathrooms: int | None
    minimum_score: int | None
    lead_type: str
    enabled: bool
    match_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True