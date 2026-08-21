import uuid
from datetime import datetime
from pydantic import BaseModel


class LeadScoreRuleOut(BaseModel):
    id: uuid.UUID
    name: str
    rule_key: str
    points: int
    is_active: bool
    config: str | None
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadScoreRuleCreate(BaseModel):
    name: str
    rule_key: str
    points: int
    is_active: bool = True
    config: str | None = None


class LeadScoreRuleUpdate(BaseModel):
    name: str | None = None
    points: int | None = None
    is_active: bool | None = None
    config: str | None = None
