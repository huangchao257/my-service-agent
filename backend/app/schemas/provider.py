from pydantic import BaseModel
from uuid import UUID


class ProviderCreate(BaseModel):
    name: str
    provider: str = "openai"
    api_base: str
    api_key: str
    models: list[str] = []
    is_active: bool = True


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    models: list[str] | None = None
    is_active: bool | None = None


class ProviderResponse(BaseModel):
    id: UUID
    name: str
    provider: str
    api_base: str
    api_key: str
    models: list[str]
    is_active: bool

    model_config = {"from_attributes": True}