"""
FastAPI 应用入口

注册所有 API 路由和 CORS 中间件。
使用 lifespan 事件在启动时自动初始化数据库表。
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.logging import setup_logging, get_logger
from app.core.rate_limit import rate_limit_middleware
from app.database import init_db
from app.api.agents import router as agents_router
from app.api.providers import router as providers_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router
from app.api.mcp_servers import router as mcp_servers_router
from app.api.skills import router as skills_router
from app.api.memories import router as memories_router
from app.api.llm_interactions import router as llm_interactions_router
from app.api.tools import router as tools_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    """应用生命周期：启动时初始化日志与数据库"""
    setup_logging()
    await init_db()
    yield


app = FastAPI(title="Agent Platform", lifespan=lifespan)
logger = get_logger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：返回统一 JSON 错误结构，避免泄露堆栈给客户端。

    HTTPException 由 FastAPI 自身处理，走到这里的都是未预期异常。"""
    logger.error("unhandled_exception", extra={
        "path": request.url.path, "error": type(exc).__name__, "msg": str(exc),
    })
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error", "error": type(exc).__name__},
    )

# CORS 配置 — 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 限流中间件（仅 /api/chat）
app.middleware("http")(rate_limit_middleware)

# 注册 API 路由
app.include_router(agents_router)           # Agent CRUD
app.include_router(providers_router)       # LLM Provider CRUD
app.include_router(conversations_router)   # 会话管理
app.include_router(chat_router)            # SSE 流式聊天
app.include_router(mcp_servers_router)     # MCP 服务器配置
app.include_router(skills_router)          # 技能模板管理
app.include_router(memories_router)        # 记忆查看/删除
app.include_router(llm_interactions_router)  # LLM 交互记录
app.include_router(tools_router)            # 内置工具发现


@app.get("/api/health")
async def health():
    """健康检查端点（轻量，不探测依赖）"""
    return {"status": "ok"}


@app.get("/api/health/deep")
async def health_deep():
    """深度健康检查：探测数据库与缓存（Redis/内存）可用性。

    返回 {status, db, cache, cache_mode}。status 为 ok 当且仅当所有依赖可用。
    任何探测失败都不抛异常，而是把错误信息写入对应字段。"""
    from sqlalchemy import text
    from app.database import async_session
    from app.core.cache import cache

    result = {"status": "ok", "db": "ok", "cache": "ok", "cache_mode": None}

    # 探测数据库
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        result["db"] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    # 探测缓存（触发惰性初始化）
    try:
        await cache.set("health:probe", "1", ttl=5)
        got = await cache.get("health:probe")
        if got != "1":
            result["cache"] = "error: readback mismatch"
            result["status"] = "degraded"
        result["cache_mode"] = cache.mode
    except Exception as e:
        result["cache"] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    return result