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