"""AI Agent 配置模型。

model 字段使用 "provider名称/model名称" 格式（如 "zmn/gpt-4o"）。
运行时解析：provider名称 → LLMProvider 记录 → 实际 API 凭证。
model名称部分加上 provider 前缀后成为 litellm 可识别的模型字符串。

tools/mcp_servers/skills 是 JSON 数组，存储工具/MCP/技能的名称，
运行时分别对 tool_registry、MCP 注册表、技能注册表做解析。"""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[str] = mapped_column(String(10), default="🤖")
    system_prompt: Mapped[str] = mapped_column(String(4096), default="You are a helpful assistant.")
    model: Mapped[str] = mapped_column(String(255), nullable=False)  # "provider名称/model名称"
    tools: Mapped[list] = mapped_column(JSON, default=list)  # 该 Agent 可用的工具名称列表
    mcp_servers: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())