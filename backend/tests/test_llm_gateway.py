"""LLM 网关单测 — 用伪造的 litellm 响应验证流式事件解析与 token 用量捕获。

通过 monkeypatch litellm.acompletion 返回预设的伪 chunk 流，
不发起真实网络请求。"""
import types
import pytest

from app.core import llm_gateway as gw_mod
from app.core.llm_gateway import LLMGateway


def _chunk(*, content=None, tool_calls=None, usage=None, with_choices=True):
    """构造一个伪 litellm chunk。"""
    delta = types.SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = types.SimpleNamespace(delta=delta)
    return types.SimpleNamespace(
        choices=[choice] if with_choices else [],
        usage=usage,
    )


def _tool_call(idx, name=None, arguments=None):
    fn = types.SimpleNamespace(name=name, arguments=arguments)
    return types.SimpleNamespace(index=idx, function=fn)


@pytest.mark.asyncio
async def test_stream_emits_delta_and_done(monkeypatch):
    """普通文本流：产出 delta + done，done 携带 usage。"""
    chunks = [_chunk(content="Hello "), _chunk(content="world")]
    usage_obj = types.SimpleNamespace(
        model_dump=lambda: {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
    )
    chunks.append(_chunk(with_choices=False, usage=usage_obj))

    async def fake_acompletion(**kwargs):
        async def gen():
            for c in chunks:
                yield c
        return gen()
    monkeypatch.setattr(gw_mod.litellm, "acompletion", fake_acompletion)

    gw = LLMGateway()
    events = []
    async def collect():
        stream = await gw.chat_completion(model="m", messages=[], stream=True)
        async for e in stream:
            events.append(e)
    await collect()

    assert events[0] == {"type": "delta", "content": "Hello "}
    assert events[1] == {"type": "delta", "content": "world"}
    done = events[-1]
    assert done["type"] == "done"
    assert done["usage"]["total_tokens"] == 7


@pytest.mark.asyncio
async def test_stream_assembles_tool_call_across_chunks(monkeypatch):
    """tool_call 的 arguments 分多个 chunk 到达时被正确拼接。"""
    chunks = [
        _chunk(tool_calls=[_tool_call(0, name="search", arguments='{"q":"')]),
        _chunk(tool_calls=[_tool_call(0, arguments='hello")')]),
        _chunk(with_choices=False, usage=None),
    ]

    async def fake_acompletion(**kwargs):
        async def gen():
            for c in chunks:
                yield c
        return gen()
    monkeypatch.setattr(gw_mod.litellm, "acompletion", fake_acompletion)

    gw = LLMGateway()
    stream = await gw.chat_completion(model="m", messages=[], stream=True)
    events = [e async for e in stream]

    tc = [e for e in events if e["type"] == "tool_call"][0]
    assert tc["name"] == "search"
    assert tc["arguments"] == '{"q":"hello")'
    assert events[-1]["type"] == "done"
    assert events[-1]["usage"] is None


@pytest.mark.asyncio
async def test_non_stream_records_interaction(monkeypatch, db_session):
    """非流式调用传入 db/agent_id 时自动记录交互日志。"""
    import uuid
    from app.models.agent import Agent
    from app.models.llm_interaction import LLMInteraction

    agent = Agent(name="A", model="m")
    db_session.add(agent)
    await db_session.commit()

    msg = types.SimpleNamespace(content="hi")
    choice = types.SimpleNamespace(message=msg)
    fake_resp = types.SimpleNamespace(
        choices=[choice],
        model_dump_json=lambda: '{"content":"hi"}',
    )

    async def fake_acompletion(**kwargs):
        return fake_resp
    monkeypatch.setattr(gw_mod.litellm, "acompletion", fake_acompletion)

    gw = LLMGateway()
    result = await gw.chat_completion(
        model="m", messages=[{"role": "user", "content": "x"}],
        stream=False, db=db_session, agent_id=agent.id,
    )
    assert result.content == "hi"
    # 交互记录已写入
    rows = (await db_session.execute(__import__("sqlalchemy").select(LLMInteraction))).scalars().all()
    assert len(rows) == 1
    assert rows[0].model == "m"


@pytest.mark.asyncio
async def test_retry_on_transient_then_succeed(monkeypatch):
    """瞬态错误重试后成功：acompletion 前两次抛 RateLimitError，第三次成功。"""
    calls = {"n": 0}
    async def fake_acompletion(**kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _make_error("RateLimitError", 429)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

    monkeypatch.setattr(gw_mod.litellm, "acompletion", fake_acompletion)
    # 跳过真实 sleep
    async def fake_sleep(d): return None
    monkeypatch.setattr(gw_mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(gw_mod.settings, "llm_max_retries", 3)
    monkeypatch.setattr(gw_mod.settings, "llm_retry_base_delay", 0.0)

    gw = LLMGateway()
    resp = await gw.chat_completion(model="m", messages=[], stream=False)
    assert resp.content == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_no_retry_on_non_transient(monkeypatch):
    """非瞬态错误（如 400）不重试，立即抛出。"""
    calls = {"n": 0}
    async def fake_acompletion(**kwargs):
        calls["n"] += 1
        raise _make_error("BadRequestError", 400)

    monkeypatch.setattr(gw_mod.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(gw_mod.settings, "llm_max_retries", 3)
    gw = LLMGateway()
    with pytest.raises(Exception):
        await gw.chat_completion(model="m", messages=[], stream=False)
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_retry_exhausted_raises(monkeypatch):
    """瞬态错误重试用尽后抛出。"""
    calls = {"n": 0}
    async def fake_acompletion(**kwargs):
        calls["n"] += 1
        raise _make_error("ServiceUnavailableError", 503)

    monkeypatch.setattr(gw_mod.litellm, "acompletion", fake_acompletion)
    async def fake_sleep(d): return None
    monkeypatch.setattr(gw_mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(gw_mod.settings, "llm_max_retries", 2)
    monkeypatch.setattr(gw_mod.settings, "llm_retry_base_delay", 0.0)
    gw = LLMGateway()
    with pytest.raises(Exception):
        await gw.chat_completion(model="m", messages=[], stream=False)
    assert calls["n"] == 3  # 1 次初始 + 2 次重试


def _make_error(name, status_code):
    """构造一个带 status_code 属性的伪异常，匹配 _is_transient 的判断。"""
    return type(name, (Exception,), {"status_code": status_code})("err")

