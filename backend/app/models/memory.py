"""从对话中提取的长期记忆。

每条记忆附带文本嵌入向量（JSON 序列化的浮点数组）用于语义搜索。
conversation_id 可选（手动添加或迁移的记忆可能无关联会话）。
去重阈值：余弦相似度 0.95（高于则覆盖已有记录，低于则新增）。"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON 序列化的浮点数组
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())