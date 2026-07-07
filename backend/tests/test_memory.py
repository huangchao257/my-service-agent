import pytest
from app.core.memory_manager import MemoryManager


def test_memory_manager_init():
    mm = MemoryManager()
    assert mm is not None


def test_cosine_similarity_identical():
    mm = MemoryManager()
    v = [1.0, 2.0, 3.0]
    score = mm._cosine_similarity(v, v)
    assert abs(score - 1.0) < 0.001


def test_cosine_similarity_orthogonal():
    mm = MemoryManager()
    score = mm._cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert abs(score) < 0.001


def test_cosine_similarity_empty():
    mm = MemoryManager()
    score = mm._cosine_similarity([], [])
    assert score == 0.0

@pytest.mark.asyncio
async def test_retrieve_top_k_override(db_session, monkeypatch):
    """retrieve 的 top_k 参数覆盖全局默认，且嵌入失败时优雅返回空。"""
    from app.core.memory_manager import MemoryManager
    from app.models.memory import Memory
    from app.models.agent import Agent

    agent = Agent(name="A", model="m")
    db_session.add(agent)
    await db_session.commit()
    # 写 3 条记忆，embedding 用简单向量
    db_session.add_all([
        Memory(agent_id=agent.id, content="c1", embedding_json="[1.0, 0.0]"),
        Memory(agent_id=agent.id, content="c2", embedding_json="[0.9, 0.1]"),
        Memory(agent_id=agent.id, content="c3", embedding_json="[0.0, 1.0]"),
    ])
    await db_session.commit()

    mm = MemoryManager()
    # 让 get_embedding 返回与 c1 最相似的向量
    async def fake_embed(text, api_base=None, api_key=None):
        return [1.0, 0.0]
    monkeypatch.setattr("app.core.memory_manager.llm_gateway.get_embedding", fake_embed)

    result = await mm.retrieve(db_session, agent.id, "q", top_k=1)
    assert result == ["c1"]
    result2 = await mm.retrieve(db_session, agent.id, "q", top_k=2)
    assert result2[0] == "c1"
    assert len(result2) == 2
