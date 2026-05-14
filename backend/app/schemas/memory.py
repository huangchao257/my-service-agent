from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class MemoryResponse(BaseModel):
    id: UUID
    agent_id: UUID
    conversation_id: UUID | None
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}