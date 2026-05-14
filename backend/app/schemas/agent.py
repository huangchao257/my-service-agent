from pydantic import BaseModel, Field
from uuid import UUID


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    avatar: str = "🤖"
    system_prompt: str = "You are a helpful assistant."
    model: str
    tools: list[str] = []
    mcp_servers: list[str] = []
    skills: list[str] = []
    temperature: float = 0.7
    max_tokens: int = 4096


class AgentUpdate(BaseModel):
    name: str | None = None
    avatar: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    mcp_servers: list[str] | None = None
    skills: list[str] | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    avatar: str
    system_prompt: str
    model: str
    tools: list[str]
    mcp_servers: list[str]
    skills: list[str]
    temperature: float
    max_tokens: int

    model_config = {"from_attributes": True}