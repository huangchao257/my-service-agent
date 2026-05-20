"""Provider Schema — 请求/响应数据模型

LLM Provider（LLM 提供商）配置的数据模型。
api_key 在列表返回时会做脱敏处理。
"""

from pydantic import BaseModel
from uuid import UUID


class ProviderCreate(BaseModel):
    """创建 Provider 请求"""
    name: str            # 自定义名称（如 "my-openai"）
    provider: str = "openai"  # 提供商类型（openai/anthropic 等）
    api_base: str        # API 端点地址
    api_key: str         # API 密钥
    models: list[str] = []   # 可用模型列表
    is_active: bool = True   # 是否启用


class ProviderUpdate(BaseModel):
    """更新 Provider 请求，仅传入需要修改的字段"""
    name: str | None = None
    provider: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    models: list[str] | None = None
    is_active: bool | None = None


class ProviderResponse(BaseModel):
    """Provider 响应"""
    id: UUID
    name: str
    provider: str
    api_base: str
    api_key: str         # 列表接口中已脱敏（前4位 + **** + 后4位）
    models: list[str]
    is_active: bool

    model_config = {"from_attributes": True}