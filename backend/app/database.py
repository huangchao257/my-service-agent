"""
数据库 — SQLAlchemy async 引擎配置

使用 async_sessionmaker 管理异步数据库会话。
启动时自动创建所有 ORM 模型对应的表（Base.metadata.create_all）。
get_db() 作为 FastAPI 依赖注入，确保每个请求使用独立的数据库会话。
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 创建异步数据库引擎
# SQLite 需要 check_same_thread=False，PostgreSQL 不需要
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# 会话工厂 — expire_on_commit=False 避免提交后属性过期
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 基类，所有模型继承自此"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：为每个请求提供独立的数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """应用启动时初始化数据库，创建所有 ORM 表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)