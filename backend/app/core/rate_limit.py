"""简单的进程内令牌桶限流中间件。

按客户端 IP 限流，主要保护 SSE chat 接口被刷。多实例部署应替换为 Redis 版本。

设计：
- 每个窗口（默认 60s）内每个 IP 最多 max_requests 次请求
- 超限返回 429 JSON
- 仅对 /api/chat 路径生效，避免影响 CRUD 接口
"""
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings


class RateLimiter:
    """进程内滑动窗口限流器。"""

    def __init__(self, max_requests: int = 20, window: float = 60.0):
        self.max_requests = max_requests
        self.window = window
        # ip -> [timestamps...]
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, ip: str) -> bool:
        """返回是否允许本次请求。"""
        now = time.monotonic()
        hits = self._hits[ip]
        # 清理过期时间戳
        cutoff = now - self.window
        self._hits[ip] = [t for t in hits if t > cutoff]
        if len(self._hits[ip]) >= self.max_requests:
            return False
        self._hits[ip].append(now)
        return True


# 全局限流器实例：每 IP 60 秒内最多 30 次 chat 请求
rate_limiter = RateLimiter(max_requests=30, window=60.0)


async def rate_limit_middleware(request: Request, call_next):
    """仅对 /api/chat 限流。其他路径直接放行。"""
    path = request.url.path
    if path.startswith("/api/chat"):
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.check(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded, too many chat requests"},
            )
    return await call_next(request)
