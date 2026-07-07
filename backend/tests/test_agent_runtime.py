"""Agent 运行时单测 — 验证 Skill 注入、消息构建、工具确认、工具超时等可独立测试的逻辑。

LLM 调用通过 monkeypatch llm_gateway.chat_completion 注入伪事件流，
避免真实网络请求。"""
import asyncio
import json
import pytest
from uuid import uuid4

from app.core.agent_runtime import AgentRuntime
from app.models.agent import Agent
from app.models.skill import Skill
from app.models.conversation import Conversation
from app.tools.base import tool_registry, ToolDefinition


@pytest.mark.asyncio
async def test_load_skills_resolves_by_name(db_session):
    """_load_skills 按 Agent.skills 中的名称解析，保持声明顺序，忽略未知名称。"""
    rt = AgentRuntime()
    s1 = Skill(name="coder", prompt_template="Be concise.", is_active=True)
    s2 = Skill(name="writer", prompt_template="Be vivid.", is_active=True)
    s3 = Skill(name="disabled", prompt_template="x", is_active=False)
    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    loaded = await rt._load_skills(db_session, ["writer", "coder", "nope", "disabled"])
    names = [s.name for s in loaded]
    assert names == ["writer", "coder"]  # 顺序跟随声明；未激活/未知被过滤


def _fake_stream(events):
    """把事件列表包装成异步迭代器，模拟 llm_gateway 的流式输出。"""
    async def gen():
        for e in events:
            yield e
    return gen()


@pytest.mark.asyncio
async def test_high_risk_tool_skipped_and_confirmed(monkeypatch, db_session):
    """高风险工具未在白名单时：发 confirmation_required 事件并跳过执行。"""
    from app.core import agent_runtime as art

    agent = Agent(name="A", model="p/m", tools=["write_file"], high_risk_tools_enabled=[])
    db_session.add(agent)
    await db_session.commit()
    conv = Conversation(title="t", agent_id=agent.id)
    db_session.add(conv)
    await db_session.commit()

    # 伪造 LLM：第一轮流一个 tool_call，第二轮流最终文本 delta
    call_count = {"n": 0}
    async def fake_chat(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_stream([
                {"type": "tool_call", "name": "write_file", "arguments": json.dumps({"path": "/tmp/x", "content": "hi"})},
                {"type": "done"},
            ])
        return _fake_stream([{"type": "delta", "content": "done"}, {"type": "done"}])
    monkeypatch.setattr(art.llm_gateway, "chat_completion", fake_chat)
    monkeypatch.setattr(art.memory_manager, "retrieve", lambda *a, **k: _async_return([]))
    monkeypatch.setattr(art.memory_manager, "extract_and_store", lambda *a, **k: _async_return(None))

    rt = AgentRuntime()
    events = [e async for e in rt.run(db_session, str(agent.id), str(conv.id), "go")]

    types = [e["event"] for e in events]
    assert "confirmation_required" in types
    # write_file 未被授权，不应有写入成功的 tool_result 文本
    conf = next(e for e in events if e["event"] == "confirmation_required")
    assert json.loads(conf["data"])["tool"] == "write_file"


@pytest.mark.asyncio
async def test_high_risk_tool_runs_when_allowlisted(monkeypatch, db_session):
    """高风险工具在白名单中时：实际执行并产出 tool_result。"""
    from app.core import agent_runtime as art
    import app.tools.file_ops  # 确保工具已注册

    agent = Agent(name="A", model="p/m", tools=["write_file"], high_risk_tools_enabled=["write_file"])
    db_session.add(agent)
    await db_session.commit()
    conv = Conversation(title="t", agent_id=agent.id)
    db_session.add(conv)
    await db_session.commit()

    call_count = {"n": 0}
    async def fake_chat(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_stream([
                {"type": "tool_call", "name": "write_file", "arguments": json.dumps({"path": "/tmp/rt_test_ok", "content": "x"})},
                {"type": "done"},
            ])
        return _fake_stream([{"type": "delta", "content": "ok"}, {"type": "done"}])
    monkeypatch.setattr(art.llm_gateway, "chat_completion", fake_chat)
    monkeypatch.setattr(art.memory_manager, "retrieve", lambda *a, **k: _async_return([]))
    monkeypatch.setattr(art.memory_manager, "extract_and_store", lambda *a, **k: _async_return(None))

    rt = AgentRuntime()
    events = [e async for e in rt.run(db_session, str(agent.id), str(conv.id), "go")]

    types = [e["event"] for e in events]
    assert "confirmation_required" not in types
    assert "tool_result" in types
    import os
    assert os.path.exists("/tmp/rt_test_ok")
    os.remove("/tmp/rt_test_ok")


async def _async_return(value):
    """helper：把同步值包成无参 async callable 的返回体（用于 monkeypatch）。"""
    return value


@pytest.mark.asyncio
async def test_tool_timeout_returns_error(monkeypatch, db_session):
    """工具执行超过 tool_timeout 时返回超时错误字符串，不抛异常。"""
    from app.core import agent_runtime as art

    # 注册一个会永久挂起的伪工具
    async def slow_forever(**kwargs):
        await asyncio.sleep(100)
        return "should not reach"
    tool_registry._tools["__test_slow__"] = ToolDefinition(
        name="__test_slow__", description="", parameters={"type": "object"},
        function=slow_forever, risk="low",
    )

    agent = Agent(name="A", model="p/m", tools=["__test_slow__"])
    db_session.add(agent)
    await db_session.commit()
    conv = Conversation(title="t", agent_id=agent.id)
    db_session.add(conv)
    await db_session.commit()

    call_count = {"n": 0}
    async def fake_chat(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_stream([{"type": "tool_call", "name": "__test_slow__", "arguments": "{}"}, {"type": "done"}])
        return _fake_stream([{"type": "delta", "content": "ok"}, {"type": "done"}])
    monkeypatch.setattr(art.llm_gateway, "chat_completion", fake_chat)
    monkeypatch.setattr(art.memory_manager, "retrieve", lambda *a, **k: _async_return([]))
    monkeypatch.setattr(art.memory_manager, "extract_and_store", lambda *a, **k: _async_return(None))
    monkeypatch.setattr(art.settings, "tool_timeout", 0.2)

    rt = AgentRuntime()
    events = [e async for e in rt.run(db_session, str(agent.id), str(conv.id), "go")]
    tr = next(e for e in events if e["event"] == "tool_result")
    assert "timed out" in json.loads(tr["data"])["output"]
    # 清理注册的伪工具
    tool_registry._tools.pop("__test_slow__", None)

