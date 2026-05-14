from pydantic import BaseModel
from uuid import UUID


class MCPServerCreate(BaseModel):
    name: str
    transport: str = "stdio"
    command: str | None = None
    args_json: str = "[]"
    url: str | None = None
    env_json: str = "{}"
    is_active: bool = True


class MCPServerUpdate(BaseModel):
    name: str | None = None
    transport: str | None = None
    command: str | None = None
    args_json: str | None = None
    url: str | None = None
    env_json: str | None = None
    is_active: bool | None = None


class MCPServerResponse(BaseModel):
    id: UUID
    name: str
    transport: str
    command: str | None
    args_json: str
    url: str | None
    env_json: str
    is_active: bool

    model_config = {"from_attributes": True}