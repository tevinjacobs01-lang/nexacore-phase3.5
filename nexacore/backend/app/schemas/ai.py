import uuid
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    limit: int = 200  # cap how many properties get sent as context


class AIResponse(BaseModel):
    answer: str


class PrioritizeRequest(BaseModel):
    limit: int = 50
