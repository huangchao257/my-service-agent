"""记忆 Schema — 记忆响应数据模型

记忆由 agent_runtime 在每轮对话后自动提取和去重存储。
关联到 agent 和 conversation，前端可按会话筛选查看。
"""

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class MemoryResponse(BaseModel):
    """记忆响应"""
    id: UUID
    agent_id: UUID
    conversation_id: UUID | None  # 关联的会话 ID（可为空）
    content: str                   # 记忆文本内容
    created_at: datetime

    model_config = {"from_attributes": True}