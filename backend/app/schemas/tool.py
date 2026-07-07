"""Tool Schema — 工具发现接口的响应模型。"""

from pydantic import BaseModel


class ToolResponse(BaseModel):
    """已注册工具的描述，供前端选择 Agent 可用工具。"""
    name: str
    description: str
    parameters: dict
    risk: str = "low"
    category: str = "general"

    model_config = {"from_attributes": True}
