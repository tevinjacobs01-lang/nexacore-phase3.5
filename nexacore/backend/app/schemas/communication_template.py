import uuid
from datetime import datetime
from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    template_type: str
    subject: str | None = None
    body: str


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body: str | None = None


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    template_type: str
    subject: str | None
    body: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RenderTemplateRequest(BaseModel):
    lead_id: uuid.UUID | None = None
    extra_variables: dict[str, str] = {}
