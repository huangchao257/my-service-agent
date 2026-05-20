"""LLM 交互记录 Schema

记录每次 LLM 调用的完整快照：
- messages_json: 发送给模型的完整消息数组（含 system prompt、记忆、历史）
- response_json: 模型返回的完整响应
- token_usage_json: token 用量统计
- duration_ms: 调用耗时（毫秒）
"""

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class LLMInteractionResponse(BaseModel):
    """LLM 交互记录响应"""
    id: UUID
    agent_id: UUID
    conversation_id: UUID | None   # 关联的会话 ID（可为空）
    model: str                      # 实际使用的模型名称
    messages_json: str              # 发送给模型的完整消息 JSON
    response_json: str | None       # 模型响应 JSON
    token_usage_json: str | None    # token 用量 JSON
    duration_ms: int | None         # 调用耗时（毫秒）
    created_at: datetime

    model_config = {"from_attributes": True}


class LLMInteractionListResponse(BaseModel):
    """LLM 交互记录分页列表响应"""
    items: list[LLMInteractionResponse]
    total: int