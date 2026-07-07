"""MCP 管理器单测 — 用伪造客户端验证 schema 转换、工具分发与优雅降级。

不依赖真实 `mcp` 库或网络，全部通过注入假 client_factory 完成。"""
import pytest

from app.core.mcp_manager import MCPManager
from app.models.mcp_server import MCPServer


class _FakeClient:
    """可控的 MCP 客户端替身：按预设返回连接结果/工具列表/调用结果。"""

    def __init__(self, server, *, connect_ok=True, tools=None, call_result="ok"):
        self.server = server
        self._connect_ok = connect_ok
        self._tools = tools or []
        self._call_result = call_result
        self.closed = False

    async def connect(self):
        return self._connect_ok

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name, arguments):
        return self._call_result

    async def close(self):
        self.closed = True


def _make_server(name="mcptest", transport="http", url="http://x/sse", is_active=True):
    return MCPServer(name=name, transport=transport, url=url, is_active=is_active)


@pytest.mark.asyncio
async def test_get_schemas_aggregates_and_indexes_owner():
    """连接成功的服务器工具被聚合，tool_owner 索引指向服务器名。"""
    server = _make_server("svc1")
    fake = _FakeClient(server, tools=[
        {"name": "search", "description": "search things", "input_schema": {"type": "object"}},
        {"name": "fetch", "description": "", "input_schema": None},
    ])
    mgr = MCPManager(client_factory=lambda s: fake)

    schemas = await mgr.get_schemas([server])
    names = [s["function"]["name"] for s in schemas]
    assert names == ["search", "fetch"]
    # 空描述被填充默认值
    assert "MCP tool: fetch" in schemas[1]["function"]["description"]
    assert mgr.has_tool("search")
    assert mgr.has_tool("fetch")
    await mgr.close()


@pytest.mark.asyncio
async def test_get_schemas_skips_unreachable_server():
    """连接失败的服务器被静默跳过，不抛异常。"""
    server = _make_server("down")
    fake = _FakeClient(server, connect_ok=False)
    mgr = MCPManager(client_factory=lambda s: fake)
    schemas = await mgr.get_schemas([server])
    assert schemas == []
    assert not mgr.has_tool("anything")
    await mgr.close()


@pytest.mark.asyncio
async def test_call_tool_dispatches_to_correct_server():
    server = _make_server("svc1")
    fake = _FakeClient(server, tools=[{"name": "ping", "description": "", "input_schema": {"type": "object"}}], call_result="pong")
    mgr = MCPManager(client_factory=lambda s: fake)
    await mgr.get_schemas([server])

    result = await mgr.call_tool("ping", {})
    assert result == "pong"
    # 未知工具返回错误字符串而非抛异常
    assert "unknown" in await mgr.call_tool("nope", {})
    await mgr.close()


@pytest.mark.asyncio
async def test_inactive_server_ignored():
    server = _make_server("inactive", is_active=False)
    fake = _FakeClient(server, tools=[{"name": "x", "description": "", "input_schema": {"type": "object"}}])
    mgr = MCPManager(client_factory=lambda s: fake)
    assert await mgr.get_schemas([server]) == []
    await mgr.close()
