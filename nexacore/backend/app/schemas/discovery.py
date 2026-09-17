import uuid
from datetime import datetime

from pydantic import BaseModel


class DiscoveryReviewRequest(BaseModel):
    classification: str
    qualification_status: str
    reason: str | None = None


class DiscoveryPromotionOut(BaseModel):
    opportunity_id: uuid.UUID
    contact_id: uuid.UUID
    lead_id: uuid.UUID
    lead_status: str
    contact_created: bool
    lead_created: bool
    message: str
    task_id: uuid.UUID | None = None
    task_created: bool = False
    recommended_action: str | None = None
    opportunity_score: int = 0
    data_confidence: str = "unknown"


class DiscoveryPromotionRequest(BaseModel):
    create_task: bool = False


class DiscoveryContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class DiscoveryOpportunityOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    classification: str
    qualification_status: str
    qualification_reason: str | None
    discovery_score: int
    opportunity_score: int
    signal_score: int
    data_confidence: str
    intelligence_reasons: list[str]
    recommended_action: str | None
    historical_signals: list[dict]
    score_band: str
    score_reasons: list[str]
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    crm_status: str = "not_promoted"
    promotion_eligible: bool = False
    promotion_block_reason: str | None = None
    lead_id: uuid.UUID | None = None
    lead_status: str | None = None
    property: dict
    observation: dict | None
    duplicate: dict | None


class DiscoveryEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    property_id: uuid.UUID | None
    opportunity_id: uuid.UUID | None
    observation_id: uuid.UUID | None
    payload: str | None
    is_read: bool
    created_at: datetime


class DiscoveryOpportunityListOut(BaseModel):
    items: list[DiscoveryOpportunityOut]
    total: int
    metrics: dict[str, int]
