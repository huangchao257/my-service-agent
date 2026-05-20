"""会话 Schema — 会话与消息的数据模型"""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ConversationCreate(BaseModel):
    """创建会话请求"""
    agent_id: UUID            # 所属 Agent ID
    title: str = "New Chat"   # 会话标题（首次对话后自动更新）


class ConversationResponse(BaseModel):
    """会话响应"""
    id: UUID
    agent_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """消息响应"""
    id: UUID
    conversation_id: UUID
    role: str        # user / assistant / tool
    content: str     # 消息文本内容
    created_at: datetime

    model_config = {"from_attributes": True}