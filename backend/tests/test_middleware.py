"""中间件单测 — 限流器与全局异常处理。"""
import uuid
import pytest

from app.core.rate_limit import RateLimiter


def test_rate_limiter_allows_under_limit():
    rl = RateLimiter(max_requests=3, window=60)
    assert rl.check("1.2.3.4") is True
    assert rl.check("1.2.3.4") is True
    assert rl.check("1.2.3.4") is True
    assert rl.check("1.2.3.4") is False  # 第 4 次超限


def test_rate_limiter_independent_per_ip():
    rl = RateLimiter(max_requests=1, window=60)
    assert rl.check("a") is True
    assert rl.check("a") is False
    assert rl.check("b") is True  # 不同 IP 独立计数


def test_rate_limiter_window_expiry():
    """窗口过期后计数重置。"""
    rl = RateLimiter(max_requests=1, window=0.2)
    assert rl.check("x") is True
    assert rl.check("x") is False
    import time
    time.sleep(0.25)
    assert rl.check("x") is True


@pytest.mark.asyncio
async def test_chat_rate_limit_429(client):
    """连续 31 次 /api/chat 请求后第 31 次返回 429（路由本身返回 404，但限流先生效）。"""
    # 用不存在的会话 id：限流中间件在路由前执行，仍会计数
    cid = uuid.uuid4()
    for _ in range(30):
        resp = await client.post(f"/api/chat/{cid}", json={"message": "x", "agent_id": str(uuid.uuid4())})
        assert resp.status_code in (404, 400)  # 会话不存在
    # 第 31 次被限流
    resp = await client.post(f"/api/chat/{cid}", json={"message": "x", "agent_id": str(uuid.uuid4())})
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_non_chat_path_not_rate_limited(client):
    """非 chat 路径不受限流影响。"""
    for _ in range(40):
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
