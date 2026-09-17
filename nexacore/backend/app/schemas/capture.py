import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CaptureData(BaseModel):
    address: str | None = None
    suburb: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    listing_reference: str | None = None
    agent_name: str | None = None
    agency_name: str | None = None
    listing_type: str | None = None
    property_type: str | None = None
    asking_price: float | None = Field(default=None, ge=0)
    monthly_rental: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    garages: int | None = Field(default=None, ge=0)
    floor_size_sqm: float | None = Field(default=None, ge=0)
    stand_size_sqm: float | None = Field(default=None, ge=0)
    notes: str | None = None
    seller_type: str | None = None
    is_owner_listed: bool | None = None
    contact_name: str | None = None
    contact_number: str | None = None
    email: str | None = None
    source_url: str | None = None
    portal_contact_methods: list[str] | None = None
    owner_evidence: str | None = None


class CaptureReview(BaseModel):
    extracted_data: CaptureData


class CaptureOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    content_type: str | None
    status: str
    extraction_method: str
    extracted_data: dict
    extraction_notes: str | None
    extraction_status: str = "review_required"
    extracted_field_confidence: dict[str, str] = {}
    extracted_candidates: dict[str, list[str]] = {}
    raw_text_detected: bool = False
    property_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    opportunity_id: uuid.UUID | None
    review_status: str = "review_required"
    qualification_status: str | None = None
    classification: str | None = None
    crm_status: str = "not_promoted"
    promotion_eligible: bool = False
    promotion_block_reason: str | None = None
    lead_id: uuid.UUID | None = None
    lead_status: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True