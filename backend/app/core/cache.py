"""缓存抽象层 — 基于 Redis 的异步缓存，Redis 不可用时降级为进程内内存字典。

设计：
- get/set/delete 都是 async，调用方无需关心底层是 Redis 还是内存
- 首次连接 Redis 失败即进入降级模式，后续不再重试连接（避免每次请求都超时）
- 内存模式仅用于单实例部署或开发；多实例部署需确保 Redis 可用
- TTL：Redis 用 EXPIRE；内存用记录的过期时间戳，惰性清理
"""
import asyncio
import time
from typing import Any

from app.config import settings


class _InMemoryBackend:
    """进程内字典后端，支持 TTL 惰性过期。"""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}  # key -> (expire_at|0, value)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expire_at, value = entry
            if expire_at and time.monotonic() > expire_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        async with self._lock:
            expire_at = (time.monotonic() + ttl) if ttl else 0
            self._store[key] = (expire_at, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def flush(self) -> None:
        async with self._lock:
            self._store.clear()


class Cache:
    """统一的异步缓存接口。Redis 不可用时透明降级到内存。"""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.redis_url
        self._redis = None
        self._mode: str | None = None  # "redis" | "memory"，None=未初始化
        self._fallback = _InMemoryBackend()

    async def _ensure(self):
        """惰性初始化 Redis 连接。失败则永久降级到内存模式。"""
        if self._mode is not None:
            return
        try:
            import redis.asyncio as aioredis  # type: ignore
            client = aioredis.from_url(self._redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            self._mode = "redis"
        except Exception:
            # 降级，后续不再尝试 Redis
            self._mode = "memory"

    async def get(self, key: str) -> Any:
        await self._ensure()
        if self._mode == "redis":
            try:
                return await self._redis.get(key)
            except Exception:
                # 运行期 Redis 故障：退回内存
                return await self._fallback.get(key)
        return await self._fallback.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        await self._ensure()
        if self._mode == "redis":
            try:
                if ttl:
                    await self._redis.set(key, value, ex=int(ttl) if ttl >= 1 else 1)
                else:
                    await self._redis.set(key, value)
                return
            except Exception:
                pass
        await self._fallback.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await self._ensure()
        if self._mode == "redis":
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        await self._fallback.delete(key)

    @property
    def mode(self) -> str | None:
        return self._mode


# 全局缓存实例
cache = Cache()
