"""MCP Server Schema — 请求/响应数据模型

MCP（Model Context Protocol）服务器配置的数据模型。
transport 字段决定连接方式：
- "stdio"：通过 command + args + env 启动本地进程
- "http"：通过 url 连接远程 SSE 端点
"""

from pydantic import BaseModel
from uuid import UUID


class MCPServerCreate(BaseModel):
    """创建 MCP 服务器配置请求"""
    name: str                       # 服务器名称
    transport: str = "stdio"        # 传输方式："stdio" 或 "http"
    command: str | None = None      # stdio 模式下的启动命令
    args_json: str = "[]"           # CLI 参数 JSON 数组
    url: str | None = None          # HTTP 模式下的远程端点 URL
    env_json: str = "{}"            # 环境变量 JSON 对象
    is_active: bool = True          # 是否启用


class MCPServerUpdate(BaseModel):
    """更新 MCP 服务器配置请求，仅传入需要修改的字段"""
    name: str | None = None
    transport: str | None = None
    command: str | None = None
    args_json: str | None = None
    url: str | None = None
    env_json: str | None = None
    is_active: bool | None = None


class MCPServerResponse(BaseModel):
    """MCP 服务器配置响应"""
    id: UUID
    name: str
    transport: str
    command: str | None
    args_json: str
    url: str | None
    env_json: str
    is_active: bool

    model_config = {"from_attributes": True}