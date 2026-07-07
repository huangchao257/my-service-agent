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
    high_risk_tools_enabled: list[str] = []           # 已授权执行的高风险工具白名单
    temperature: float = 0.7                          # LLM 温度参数
    max_tokens: int = 4096                            # 最大输出 token 数
    history_limit: int = 20                           # 每轮注入的历史消息条数上限
    memory_top_k: int | None = None                   # 记忆检索条数，None 用全局默认


class AgentUpdate(BaseModel):
    """更新 Agent 请求，仅传入需要修改的字段"""
    name: str | None = None
    avatar: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    mcp_servers: list[str] | None = None
    skills: list[str] | None = None
    high_risk_tools_enabled: list[str] | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    history_limit: int | None = None
    memory_top_k: int | None = None


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
    high_risk_tools_enabled: list[str]
    temperature: float
    max_tokens: int
    history_limit: int
    memory_top_k: int | None

    model_config = {"from_attributes": True}