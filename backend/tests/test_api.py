import pytest


@pytest.mark.asyncio
async def test_list_agents_empty(client):
    resp = await client.get("/api/agents")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_agent(client):
    resp = await client.post("/api/agents", json={
        "name": "Test Agent", "model": "gpt-4o", "tools": ["calculator"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Agent"
    assert data["model"] == "gpt-4o"
    assert data["tools"] == ["calculator"]


@pytest.mark.asyncio
async def test_update_agent(client):
    create_resp = await client.post("/api/agents", json={"name": "Old", "model": "gpt-4o"})
    agent_id = create_resp.json()["id"]
    resp = await client.put(f"/api/agents/{agent_id}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_agent(client):
    create_resp = await client.post("/api/agents", json={"name": "ToDelete", "model": "gpt-4o"})
    agent_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/agents/{agent_id}")
    assert resp.status_code == 204
    list_resp = await client.get("/api/agents")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_list_providers_empty(client):
    resp = await client.get("/api/providers")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_provider(client):
    resp = await client.post("/api/providers", json={
        "name": "OpenAI", "provider": "openai",
        "api_base": "https://api.openai.com/v1", "api_key": "sk-test",
        "models": ["gpt-4o"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "OpenAI"
    assert data["api_key"] == "sk-test"


@pytest.mark.asyncio
async def test_create_conversation(client):
    agent_resp = await client.post("/api/agents", json={"name": "Test", "model": "gpt-4o"})
    agent_id = agent_resp.json()["id"]
    resp = await client.post("/api/conversations", json={"agent_id": agent_id, "title": "Test Chat"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Chat"
    assert data["agent_id"] == agent_id


@pytest.mark.asyncio
async def test_list_conversations(client):
    agent_resp = await client.post("/api/agents", json={"name": "Test", "model": "gpt-4o"})
    agent_id = agent_resp.json()["id"]
    await client.post("/api/conversations", json={"agent_id": agent_id})
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_agent_by_id(client):
    """GET /api/agents/{id} 返回单条 Agent，不存在时 404"""
    create_resp = await client.post("/api/agents", json={"name": "Single", "model": "gpt-4o"})
    agent_id = create_resp.json()["id"]
    resp = await client.get(f"/api/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Single"
    not_found = await client.get(f"/api/agents/{__import__('uuid').uuid4()}")
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_get_provider_by_id_masked(client):
    """GET /api/providers/{id} 返回脱敏后的 api_key"""
    create_resp = await client.post("/api/providers", json={
        "name": "OpenAI", "provider": "openai",
        "api_base": "https://api.openai.com/v1", "api_key": "sk-test-1234567890",
        "models": ["gpt-4o"],
    })
    pid = create_resp.json()["id"]
    resp = await client.get(f"/api/providers/{pid}")
    assert resp.status_code == 200
    assert "****" in resp.json()["api_key"]


@pytest.mark.asyncio
async def test_get_skill_and_mcp_by_id(client):
    """GET 单条 skill / mcp-server"""
    skill_resp = await client.post("/api/skills", json={
        "name": "coder", "prompt_template": "Be concise.", "category": "coding",
    })
    sid = skill_resp.json()["id"]
    assert (await client.get(f"/api/skills/{sid}")).status_code == 200
    assert (await client.get(f"/api/skills/{__import__('uuid').uuid4()}")).status_code == 404

    mcp_resp = await client.post("/api/mcp-servers", json={
        "name": "fs", "transport": "stdio", "command": "ls",
    })
    mid = mcp_resp.json()["id"]
    assert (await client.get(f"/api/mcp-servers/{mid}")).status_code == 200


@pytest.mark.asyncio
async def test_conversation_search(client):
    """GET /api/conversations?search= 按标题模糊匹配"""
    agent_resp = await client.post("/api/agents", json={"name": "T", "model": "gpt-4o"})
    aid = agent_resp.json()["id"]
    await client.post("/api/conversations", json={"agent_id": aid, "title": "Python debugging tips"})
    await client.post("/api/conversations", json={"agent_id": aid, "title": "Cooking recipe"})
    resp = await client.get("/api/conversations?search=python")
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.json()]
    assert titles == ["Python debugging tips"]
    # 大小写不敏感
    resp2 = await client.get("/api/conversations?search=COOK")
    assert [c["title"] for c in resp2.json()] == ["Cooking recipe"]


@pytest.mark.asyncio
async def test_export_conversation_markdown_and_json(db_session):
    """GET /api/conversations/{id}/export 输出 markdown / json 两种格式"""
    from app.api.conversations import export_conversation
    from app.models.agent import Agent
    from app.models.conversation import Conversation
    from app.models.message import Message

    agent = Agent(name="A", model="gpt-4o")
    db_session.add(agent)
    await db_session.commit()
    conv = Conversation(title="My Chat", agent_id=agent.id)
    db_session.add(conv)
    await db_session.commit()
    for role, content in [("user", "hi there"), ("assistant", "hello!")]:
        db_session.add(Message(conversation_id=conv.id, role=role, content=content))
    await db_session.commit()

    md = await export_conversation(conv.id, format="markdown", db=db_session)
    assert "My Chat" in md.body.decode()
    assert "hi there" in md.body.decode()
    assert "attachment" in md.headers["content-disposition"]

    import json as _json
    js = await export_conversation(conv.id, format="json", db=db_session)
    payload = _json.loads(js.body.decode())
    assert payload["title"] == "My Chat"
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["content"] == "hi there"


@pytest.mark.asyncio
async def test_memory_search(db_session):
    """GET /api/memories?search= 按内容关键词匹配（直接调用路由函数）"""
    from app.models.memory import Memory
    from app.models.agent import Agent
    from app.api.memories import list_memories

    agent = Agent(name="A", model="gpt-4o")
    db_session.add(agent)
    await db_session.commit()
    db_session.add_all([
        Memory(agent_id=agent.id, content="User prefers Python", embedding_json="[]"),
        Memory(agent_id=agent.id, content="User likes cooking", embedding_json="[]"),
    ])
    await db_session.commit()

    result = await list_memories(agent_id=None, conversation_id=None, search="python", limit=None, offset=0, db=db_session)
    assert len(result) == 1
    assert "Python" in result[0].content
    result2 = await list_memories(agent_id=None, conversation_id=None, search="cook", limit=None, offset=0, db=db_session)
    assert len(result2) == 1
    assert result2[0].content == "User likes cooking"

@pytest.mark.asyncio
async def test_duplicate_agent(client):
    """POST /api/agents/{id}/duplicate 复制 Agent，带 (copy) 后缀"""
    create_resp = await client.post("/api/agents", json={
        "name": "Helper", "model": "p/gpt-4o", "tools": ["calculator"],
        "system_prompt": "Be helpful.", "temperature": 0.5,
    })
    aid = create_resp.json()["id"]
    resp = await client.post(f"/api/agents/{aid}/duplicate")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Helper (copy)"
    assert data["model"] == "p/gpt-4o"
    assert data["tools"] == ["calculator"]
    assert data["temperature"] == 0.5
    assert data["id"] != aid  # 新身份
    # 列表里现在有两个
    assert len((await client.get("/api/agents")).json()) == 2


@pytest.mark.asyncio
async def test_agent_pagination(client):
    """GET /api/agents?limit=&offset= 分页"""
    for i in range(5):
        await client.post("/api/agents", json={"name": f"A{i}", "model": "gpt-4o"})
    page1 = (await client.get("/api/agents?limit=2&offset=0")).json()
    page2 = (await client.get("/api/agents?limit=2&offset=2")).json()
    assert len(page1) == 2
    assert len(page2) == 2
    # 两页不重叠
    ids1 = {a["id"] for a in page1}
    ids2 = {a["id"] for a in page2}
    assert ids1.isdisjoint(ids2)
    # 不传 limit 返回全部
    assert len((await client.get("/api/agents")).json()) == 5


@pytest.mark.asyncio
async def test_provider_connection_test_ok(client, monkeypatch):
    """POST /api/providers/{id}/test 连通成功返回 ok=True"""
    import litellm as _litellm
    create = await client.post("/api/providers", json={
        "name": "P", "provider": "openai", "api_base": "https://x/v1",
        "api_key": "sk-x", "models": ["gpt-4o"],
    })
    pid = create.json()["id"]

    async def fake_acompletion(**kwargs):
        return object()
    monkeypatch.setattr(_litellm, "acompletion", fake_acompletion)

    resp = await client.post(f"/api/providers/{pid}/test")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_provider_connection_test_fail(client, monkeypatch):
    """POST /api/providers/{id}/test 连通失败返回 ok=False 且不抛异常"""
    import litellm as _litellm
    create = await client.post("/api/providers", json={
        "name": "P", "provider": "openai", "api_base": "https://x/v1",
        "api_key": "sk-bad", "models": ["gpt-4o"],
    })
    pid = create.json()["id"]

    async def fake_acompletion(**kwargs):
        raise RuntimeError("auth error")
    monkeypatch.setattr(_litellm, "acompletion", fake_acompletion)

    resp = await client.post(f"/api/providers/{pid}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "auth error" in body["detail"]


@pytest.mark.asyncio
async def test_provider_refresh_models(client, monkeypatch):
    """POST /api/providers/{id}/refresh-models 拉取并更新 models 列表"""
    import httpx as _httpx

    create = await client.post("/api/providers", json={
        "name": "P", "provider": "openai", "api_base": "https://x/v1",
        "api_key": "sk-x", "models": [],
    })
    pid = create.json()["id"]

    # 伪造 httpx.AsyncClient.get 返回 200 + 模型列表
    class _FakeResp:
        status_code = 200
        def json(self):
            return {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]}

    class _FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None): return _FakeResp()

    monkeypatch.setattr(_httpx, "AsyncClient", _FakeClient)

    resp = await client.post(f"/api/providers/{pid}/refresh-models")
    assert resp.status_code == 200
    models = resp.json()["models"]
    assert sorted(models) == ["gpt-4o", "gpt-4o-mini"]  # 去重


@pytest.mark.asyncio
async def test_health_lightweight(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_deep(client):
    """深度健康检查至少返回 db/cache 字段，DB 探测在测试 SQLite 下应 ok"""
    resp = await client.get("/api/health/deep")
    assert resp.status_code == 200
    data = resp.json()
    assert "db" in data and "cache" in data
    # 测试环境 SQLite 可用，db 应为 ok
    assert data["db"] == "ok"
    # 缓存降级到 memory
    assert data["cache_mode"] in ("memory", "redis")


@pytest.mark.asyncio
async def test_provider_list_does_not_mutate_orm(db_session):
    """回归：列表脱敏不应改写 ORM 实例的 api_key（否则后续 commit 会毁掉真实密钥）。"""
    from app.models.provider import LLMProvider
    from app.api.providers import list_providers

    p = LLMProvider(name="P", provider="openai", api_base="https://x/v1",
                    api_key="sk-secret-1234567890", models=["gpt-4o"], is_active=True)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    resp = await list_providers(limit=None, offset=0, db=db_session)
    assert "****" in resp[0].api_key  # 响应已脱敏
    assert p.api_key == "sk-secret-1234567890"  # ORM 实例本身未被改写
    await db_session.commit()
    await db_session.refresh(p)
    assert p.api_key == "sk-secret-1234567890"  # commit 后仍未被破坏
