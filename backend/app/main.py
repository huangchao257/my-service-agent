"""
FastAPI 应用入口

注册所有 API 路由和 CORS 中间件。
使用 lifespan 事件在启动时自动初始化数据库表。
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.agents import router as agents_router
from app.api.providers import router as providers_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router
from app.api.mcp_servers import router as mcp_servers_router
from app.api.skills import router as skills_router
from app.api.memories import router as memories_router
from app.api.llm_interactions import router as llm_interactions_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    await init_db()
    yield


app = FastAPI(title="Agent Platform", lifespan=lifespan)

# CORS 配置 — 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(agents_router)           # Agent CRUD
app.include_router(providers_router)       # LLM Provider CRUD
app.include_router(conversations_router)   # 会话管理
app.include_router(chat_router)            # SSE 流式聊天
app.include_router(mcp_servers_router)     # MCP 服务器配置
app.include_router(skills_router)          # 技能模板管理
app.include_router(memories_router)        # 记忆查看/删除
app.include_router(llm_interactions_router)  # LLM 交互记录


@app.get("/api/health")
async def health():
    """健康检查端点"""
    return {"status": "ok"}