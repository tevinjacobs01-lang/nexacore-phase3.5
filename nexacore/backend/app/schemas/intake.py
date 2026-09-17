import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class IntakeCreate(BaseModel):
    input_type: Literal["url", "text", "screenshot"]
    value: str | None = Field(default=None, max_length=30000)
    capture_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if self.input_type == "screenshot":
            if self.capture_id is None:
                raise ValueError("A screenshot intake requires a Capture ID")
        elif not self.value or not self.value.strip():
            raise ValueError("URL and text intakes require content")
        return self


class IntakeOut(BaseModel):
    id: uuid.UUID
    input_type: str
    source_url: str | None
    source_domain: str | None
    status: str
    result_summary: str
    extracted_data: dict
    property_id: uuid.UUID | None
    capture_id: uuid.UUID | None
    opportunity_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True
