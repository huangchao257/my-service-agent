import os
import tempfile
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db
from app.core.cache import cache
from app.core.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def _reset_state():
    """每个测试前重置全局单例（缓存、限流器），避免跨测试的脏数据。"""
    cache._mode = None
    cache._redis = None
    cache._fallback._store.clear()
    rate_limiter._hits.clear()
    yield
    cache._fallback._store.clear()
    rate_limiter._hits.clear()


@pytest_asyncio.fixture
async def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite+aiosqlite:///{path}"

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()
    os.unlink(path)


@pytest_asyncio.fixture
async def client(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """提供一个干净的临时 SQLite AsyncSession，供直接操作 ORM 的单测使用。

    与 `db` fixture 分离：后者为 HTTP 客户端覆盖 get_db 依赖，
    本 fixture 则把 session 句柄直接交给测试代码。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite+aiosqlite:///{path}"

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()
    os.unlink(path)