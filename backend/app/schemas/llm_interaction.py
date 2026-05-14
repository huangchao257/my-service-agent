from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class LLMInteractionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    conversation_id: UUID | None
    model: str
    messages_json: str
    response_json: str | None
    token_usage_json: str | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LLMInteractionListResponse(BaseModel):
    items: list[LLMInteractionResponse]
    total: int