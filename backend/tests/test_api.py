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