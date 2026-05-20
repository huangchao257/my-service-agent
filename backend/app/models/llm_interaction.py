"""LLM API 调用记录，包含完整上下文快照。

messages_json：发送给模型的完整消息列表（system + 历史 + 用户）
response_json：模型返回的响应
duration_ms：API 调用耗时（毫秒）
用于调试、审计和回溯模型行为。"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMInteraction(Base):
    __tablename__ = "llm_interactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)  # litellm 模型字符串
    messages_json: Mapped[str] = mapped_column(Text, nullable=False)  # 完整上下文快照
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 模型响应
    token_usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Token 用量（如果可用）
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # API 调用延迟
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())