from pydantic import BaseModel
from uuid import UUID


class SkillCreate(BaseModel):
    name: str
    description: str = ""
    prompt_template: str
    category: str = "general"
    is_active: bool = True


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    prompt_template: str | None = None
    category: str | None = None
    is_active: bool | None = None


class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: str
    prompt_template: str
    category: str
    is_active: bool

    model_config = {"from_attributes": True}