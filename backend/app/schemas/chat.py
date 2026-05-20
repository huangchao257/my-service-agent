"""聊天 Schema — 聊天请求数据模型"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str     # 用户消息内容
    agent_id: str    # 发起对话的 Agent ID