"""缓存层单测 — 验证 get/set/delete 与 TTL 过期、内存降级。

测试环境无 Redis，Cache 会自动降级到内存后端，覆盖核心逻辑。"""
import asyncio
import pytest

from app.core.cache import Cache, _InMemoryBackend


@pytest.mark.asyncio
async def test_memory_backend_set_get_delete():
    b = _InMemoryBackend()
    await b.set("k", "v")
    assert await b.get("k") == "v"
    await b.delete("k")
    assert await b.get("k") is None


@pytest.mark.asyncio
async def test_memory_backend_ttl_expires():
    b = _InMemoryBackend()
    await b.set("k", "v", ttl=0)  # ttl=0/None 表示不过期
    await b.set("exp", "v", ttl=0.2)
    assert await b.get("exp") == "v"
    await asyncio.sleep(0.3)
    assert await b.get("exp") is None
    assert await b.get("k") == "v"


@pytest.mark.asyncio
async def test_cache_falls_back_to_memory(monkeypatch):
    """无 Redis 时 Cache 降级到内存模式，set/get 正常工作。"""
    c = Cache(redis_url="redis://localhost:1/0")  # 不可达地址
    await c.set("a", "1")
    assert c.mode == "memory"
    assert await c.get("a") == "1"
    await c.delete("a")
    assert await c.get("a") is None


@pytest.mark.asyncio
async def test_cache_ttl_memory_path():
    c = Cache(redis_url="redis://localhost:1/0")
    await c.set("k", "v", ttl=0.2)
    assert await c.get("k") == "v"
    await asyncio.sleep(0.3)
    assert await c.get("k") is None
