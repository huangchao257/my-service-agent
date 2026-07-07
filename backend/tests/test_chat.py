"""聊天 API 单测 — 验证 regenerate 端点的消息裁剪与重跑逻辑。

通过 monkeypatch agent_runtime.run 注入伪事件流，避免真实 LLM 调用。"""
import json
import pytest
import types

from app.api.chat import regenerate
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message


class _FakeRequest:
    """伪 Request，is_disconnected 永远返回 False。"""
    async def is_disconnected(self):
        return False


@pytest.mark.asyncio
async def test_regenerate_trims_and_reruns(db_session, monkeypatch):
    """regenerate 删除末尾 user/assistant 对，用原 user 文本重跑。"""
    agent = Agent(name="A", model="p/m")
    db_session.add(agent)
    await db_session.commit()
    conv = Conversation(title="t", agent_id=agent.id)
    db_session.add(conv)
    await db_session.commit()

    msgs = [
        Message(conversation_id=conv.id, role="user", content="hi"),
        Message(conversation_id=conv.id, role="assistant", content="hello"),
        Message(conversation_id=conv.id, role="user", content="bye"),
        Message(conversation_id=conv.id, role="assistant", content="bye-ans"),
        Message(conversation_id=conv.id, role="tool", content="tool-out"),
    ]
    for m in msgs:
        db_session.add(m)
    await db_session.commit()

    captured = {}
    async def fake_run(db, agent_id, conversation_id, user_message):
        captured["user_message"] = user_message
        captured["conversation_id"] = conversation_id
        yield {"event": "done", "data": json.dumps({"conversation_id": conversation_id})}
    monkeypatch.setattr("app.api.chat.agent_runtime.run", fake_run)

    resp = await regenerate(conv.id, _FakeRequest(), db=db_session)
    # 拉流以触发执行
    body = ""
    async for chunk in resp.body_iterator:
        body += chunk if isinstance(chunk, str) else chunk.decode()

    assert "done" in body
    assert captured["user_message"] == "bye"  # 用最后一条 user 文本重跑

    # 末尾 user/assistant/tool 三条被删除，只剩前两条
    remaining = (await db_session.execute(
        __import__("sqlalchemy").select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
    )).scalars().all()
    assert [m.content for m in remaining] == ["hi", "hello"]


@pytest.mark.asyncio
async def test_regenerate_no_user_message(client):
    """没有 user 消息时返回 400。"""
    agent_resp = await client.post("/api/agents", json={"name": "A", "model": "gpt-4o"})
    aid = agent_resp.json()["id"]
    conv_resp = await client.post("/api/conversations", json={"agent_id": aid})
    cid = conv_resp.json()["id"]
    resp = await client.post(f"/api/chat/{cid}/regenerate")
    assert resp.status_code == 400
