"""MCP（Model Context Protocol）服务器管理器。

把 Agent 配置的 MCP 服务器在运行时拉取的工具，统一转换为 OpenAI
function-calling schema，并在工具被调用时分发到对应服务器执行。

设计要点：
- `mcp` 库为可选依赖：未安装或连接失败时优雅降级（返回空工具/错误字符串），
  绝不抛异常阻断主对话流。
- 每个服务器的工具列表按 (server_name, tool_name) 建索引，避免命名冲突。
- 工具获取结果带 TTL 缓存，避免每轮对话都重新连接服务器。
"""
import json
import time
from typing import Any

from app.models.mcp_server import MCPServer


class _MCPClient:
    """对 `mcp` 库客户端的薄封装，便于测试时替换。

    真实实现按 transport（stdio/http）创建会话并 list_tools / call_tool。
    若 `mcp` 库未安装，所有方法返回空/错误，由上层降级处理。"""

    def __init__(self, server: MCPServer):
        self.server = server
        self._session = None
        self._client_ctx = None

    async def connect(self) -> bool:
        """建立连接。返回是否成功。失败返回 False（不抛异常）。"""
        try:
            from mcp import ClientSession  # type: ignore
            from mcp.client.stdio import stdio_client  # type: ignore
            from mcp.client.sse import sse_client  # type: ignore
        except Exception:
            return False

        try:
            args = json.loads(self.server.args_json or "[]")
            env = json.loads(self.server.env_json or "{}")
            if self.server.transport == "http" and self.server.url:
                self._client_ctx = sse_client(self.server.url)
            elif self.server.transport == "stdio" and self.server.command:
                self._client_ctx = stdio_client(self.server.command, args=args, env=env)
            else:
                return False

            read, write = await self._client_ctx.__aenter__()
            self._session = ClientSession(read, write)
            await self._session.__aenter__()
            return True
        except Exception:
            await self.close()
            return False

    async def list_tools(self) -> list[dict]:
        """返回 [{name, description, input_schema}]，失败返回空列表。"""
        if not self._session:
            return []
        try:
            result = await self._session.list_tools()
            return [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema or {"type": "object"}}
                for t in result.tools
            ]
        except Exception:
            return []

    async def call_tool(self, name: str, arguments: dict) -> str:
        """调用工具并返回字符串结果。失败返回错误字符串。"""
        if not self._session:
            return f"Error: MCP server '{self.server.name}' not connected"
        try:
            result = await self._session.call_tool(name, arguments)
            # 把 TextContent 列表拼成字符串
            texts = []
            for c in getattr(result, "content", []) or []:
                text = getattr(c, "text", None)
                if text:
                    texts.append(text)
            return "\n".join(texts) if texts else "(no output)"
        except Exception as e:
            return f"Error calling MCP tool '{name}': {e}"

    async def close(self):
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
                self._session = None
        except Exception:
            pass
        try:
            if self._client_ctx:
                await self._client_ctx.__aexit__(None, None, None)
                self._client_ctx = None
        except Exception:
            pass


class MCPManager:
    """MCP 工具聚合层：跨多个服务器收集工具 schema 并按名分发调用。"""

    # 工具列表缓存：(server_id) -> (timestamp, schemas)；TTL 秒
    _CACHE_TTL = 300

    def __init__(self, client_factory=_MCPClient):
        self._client_factory = client_factory
        self._schema_cache: dict[str, tuple[float, list[dict]]] = {}
        # 工具名 -> 提供它的服务器名（运行期由 get_schemas 填充）
        self._tool_owner: dict[str, str] = {}
        # 已连接的客户端，按服务器名索引（用于 call_tool）
        self._clients: dict[str, _MCPClient] = {}

    def _to_openai_schema(self, tool: dict) -> dict:
        """把 MCP 工具描述转为 OpenAI function-calling schema。"""
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"] or f"MCP tool: {tool['name']}",
                "parameters": tool.get("input_schema") or {"type": "object"},
            },
        }

    async def get_schemas(self, servers: list[MCPServer]) -> list[dict]:
        """聚合所有服务器的工具 schema。连接失败的服务器被静默跳过。"""
        schemas: list[dict] = []
        self._tool_owner = {}
        self._clients = {}
        for server in servers:
            if not server.is_active:
                continue
            cached = self._schema_cache.get(str(server.id))
            if cached and (time.monotonic() - cached[0]) < self._CACHE_TTL:
                server_schemas = cached[1]
            else:
                client = self._client_factory(server)
                connected = await client.connect()
                if not connected:
                    await client.close()
                    continue
                tools = await client.list_tools()
                if not tools:
                    await client.close()
                    continue
                server_schemas = [self._to_openai_schema(t) for t in tools]
                self._schema_cache[str(server.id)] = (time.monotonic(), server_schemas)
                self._clients[server.name] = client
                # 注意：保持客户端连接以备 call_tool；运行结束后由 close() 释放
            for s in server_schemas:
                name = s["function"]["name"]
                self._tool_owner[name] = server.name
                schemas.append(s)
        return schemas

    async def call_tool(self, name: str, arguments: dict) -> str:
        """按工具名找到所属服务器并执行。未知工具返回错误字符串。"""
        owner = self._tool_owner.get(name)
        if not owner:
            return f"Error: unknown MCP tool '{name}'"
        client = self._clients.get(owner)
        if not client:
            return f"Error: MCP server '{owner}' not connected"
        return await client.call_tool(name, arguments)

    def has_tool(self, name: str) -> bool:
        return name in self._tool_owner

    async def close(self):
        for client in self._clients.values():
            await client.close()
        self._clients = {}


mcp_manager = MCPManager()
