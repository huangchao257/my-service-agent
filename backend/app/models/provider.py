"""LLM API 提供商配置。

存储 API 端点和凭证。provider 字段对应 litellm 的提供商标识
（"openai"、"anthropic" 等）。name 字段是用户自定义别名，
在 Agent 的 model 字段中作为 "name/model名称" 的前半部分使用。
API Key 明文存储 — 生产环境应加密或使用密钥管理服务。"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 用户自定义别名
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # litellm 提供商类型
    api_base: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)  # 明文存储，生产环境需加密
    models: Mapped[list] = mapped_column(JSON, default=list)  # 该提供商可用的模型列表
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())