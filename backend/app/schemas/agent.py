"""Agent Schema — 请求/响应数据模型

AgentCreate: 创建 Agent 时的请求体
AgentUpdate: 更新 Agent 时的请求体（所有字段可选）
AgentResponse: API 返回的 Agent 数据
"""

from pydantic import BaseModel, Field
from uuid import UUID


class AgentCreate(BaseModel):
    """创建 Agent 请求"""
    name: str = Field(..., max_length=255)          # Agent 名称
    avatar: str = "🤖"                               # 头像 emoji
    system_prompt: str = "You are a helpful assistant."  # 系统提示词
    model: str                                        # 使用的模型标识（如 "my-provider/gpt-4o"）
    tools: list[str] = []                             # 启用的内置工具列表
    mcp_servers: list[str] = []                       # 关联的 MCP 服务器 ID 列表
    skills: list[str] = []                            # 关联的技能 ID 列表
    temperature: float = 0.7                          # LLM 温度参数
    max_tokens: int = 4096                            # 最大输出 token 数


class AgentUpdate(BaseModel):
    """更新 Agent 请求，仅传入需要修改的字段"""
    name: str | None = None
    avatar: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    mcp_servers: list[str] | None = None
    skills: list[str] | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class AgentResponse(BaseModel):
    """Agent 响应"""
    id: UUID
    name: str
    avatar: str
    system_prompt: str
    model: str
    tools: list[str]
    mcp_servers: list[str]
    skills: list[str]
    temperature: float
    max_tokens: int

    model_config = {"from_attributes": True}