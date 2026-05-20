"""技能 Schema — 请求/响应数据模型

技能是可复用的 prompt 模板，分配给 Agent 后注入到 system message。
category 用于前端分类展示。
"""

from pydantic import BaseModel
from uuid import UUID


class SkillCreate(BaseModel):
    """创建技能请求"""
    name: str                          # 技能名称
    description: str = ""              # 技能描述
    prompt_template: str               # 实际的 prompt 指令模板
    category: str = "general"          # 分类（如 coding / writing / general）
    is_active: bool = True             # 是否启用


class SkillUpdate(BaseModel):
    """更新技能请求，仅传入需要修改的字段"""
    name: str | None = None
    description: str | None = None
    prompt_template: str | None = None
    category: str | None = None
    is_active: bool | None = None


class SkillResponse(BaseModel):
    """技能响应"""
    id: UUID
    name: str
    description: str
    prompt_template: str
    category: str
    is_active: bool

    model_config = {"from_attributes": True}