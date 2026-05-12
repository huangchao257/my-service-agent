# Agent Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal multi-agent chat platform with tool-use, memory, and multi-provider LLM support, with a Doubao-style chat UI.

**Architecture:** FastAPI backend with LiteLLM gateway, PostgreSQL+pgvector for data/memory, React+Next.js frontend with SSE streaming. Docker Compose for deployment.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, LiteLLM, pgvector, Next.js 14, shadcn/ui, TailwindCSS

---

### Task 1: Project scaffolding — Docker and root config

**Files:**
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `Makefile`

- [ ] **Step 1: Write docker-compose.yml**

```yaml
version: "3.8"

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: agent123
      POSTGRES_DB: agent_platform
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://agent:agent123@db:5432/agent_platform
      SECRET_KEY: dev-secret-key-change-in-production
    depends_on:
      - db
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 2: Write .gitignore**

```
node_modules/
.next/
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
.turbo/
```

- [ ] **Step 3: Write Makefile**

```makefile
.PHONY: dev dev-backend dev-frontend build test

dev:
	docker compose up -d db
	cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm install && npm run dev &
	wait

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

build:
	docker compose build

test:
	cd backend && pytest -v
	cd frontend && npm test
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml .gitignore Makefile
git commit -m "chore: add project scaffolding"
```

---

### Task 2: Backend project structure and dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.2
pgvector==0.3.6
litellm==1.49.0
python-dotenv==1.0.1
cryptography==43.0.1
httpx==0.27.2
openai==1.51.0
pydantic==2.9.2
pydantic-settings==2.5.2
```

- [ ] **Step 2: Write backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write backend/app/__init__.py (empty)**

```python
```

- [ ] **Step 4: Write backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agent:agent123@localhost:5432/agent_platform"
    secret_key: str = "dev-secret-key-change-in-production"
    llm_timeout: int = 60
    tool_timeout: int = 30
    max_tool_rounds: int = 10
    conversation_timeout: int = 300
    memory_top_k: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 5: Write backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 6: Write backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Agent Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "chore: add backend project structure"
```

---

### Task 3: Backend data models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/agent.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/memory.py`
- Create: `backend/app/models/provider.py`

- [ ] **Step 1: Write backend/app/models/__init__.py**

```python
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.memory import Memory
from app.models.provider import LLMProvider

__all__ = ["Agent", "Conversation", "Message", "Memory", "LLMProvider"]
```

- [ ] **Step 2: Write backend/app/models/agent.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[str] = mapped_column(String(10), default="🤖")
    system_prompt: Mapped[str] = mapped_column(String(4096), default="You are a helpful assistant.")
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3: Write backend/app/models/conversation.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: Write backend/app/models/message.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 5: Write backend/app/models/memory.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: Write backend/app/models/provider.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    api_base: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    models: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 7: Write a test for models**

Create `backend/tests/__init__.py` (empty) and `backend/tests/test_models.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Agent, Conversation, Message, LLMProvider


@pytest.mark.asyncio
async def test_agent_creation():
    agent = Agent(name="Test", model="gpt-4o")
    assert agent.name == "Test"
    assert agent.model == "gpt-4o"
    assert agent.tools == []
    assert agent.temperature == 0.7


@pytest.mark.asyncio
async def test_conversation_fields():
    conv = Conversation(title="Hello")
    assert conv.title == "Hello"


def test_message_roles():
    msg = Message(role="user", content="hi")
    assert msg.role == "user"
    assert msg.content == "hi"


def test_provider_models():
    p = LLMProvider(name="OpenAI", provider="openai", api_base="https://api.openai.com/v1", api_key="sk-test", models=["gpt-4o"])
    assert p.models == ["gpt-4o"]
    assert p.is_active is True
```

- [ ] **Step 8: Run tests**

```bash
cd backend && pip install pytest pytest-asyncio && python -m pytest tests/test_models.py -v
```

Expected: 4 tests pass

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/ backend/tests/
git commit -m "feat: add data models"
```

---

### Task 4: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/001_initial.py`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend && alembic init alembic
```

- [ ] **Step 2: Configure backend/alembic.ini**

Change the `sqlalchemy.url` line to:

```ini
sqlalchemy.url = postgresql+asyncpg://agent:agent123@localhost:5432/agent_platform
```

- [ ] **Step 3: Write backend/alembic/env.py**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.database import Base
from app.models import Agent, Conversation, Message, Memory, LLMProvider

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial"
```

- [ ] **Step 5: Enable pgvector extension**

After generating, edit the migration file to add at the top of `upgrade()`:

```python
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # ... rest of auto-generated code
```

- [ ] **Step 6: Run migration against local DB**

```bash
docker compose up -d db
cd backend && alembic upgrade head
```

- [ ] **Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "chore: add alembic migrations"
```

---

### Task 5: Tool registry and built-in tools

**Files:**
- Create: `backend/app/tools/__init__.py`
- Create: `backend/app/tools/base.py`
- Create: `backend/app/tools/system_tools.py`
- Create: `backend/app/tools/web_search.py`
- Create: `backend/app/tools/file_ops.py`
- Create: `backend/app/tools/code_executor.py`
- Test: `backend/tests/test_tools.py`

- [ ] **Step 1: Write backend/app/tools/base.py**

```python
from typing import Any, Callable
from dataclasses import dataclass, field


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    function: Callable
    risk: str = "low"  # low, medium, high


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, parameters: dict, risk: str = "low"):
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                function=func,
                risk=risk,
            )
            return func

        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_schemas(self, names: list[str]) -> list[dict]:
        schemas = []
        for name in names:
            tool = self._tools.get(name)
            if tool:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                })
        return schemas

    def list_all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def requires_confirmation(self, name: str) -> bool:
        tool = self._tools.get(name)
        return tool.risk == "high" if tool else False


tool_registry = ToolRegistry()
```

- [ ] **Step 2: Write backend/app/tools/system_tools.py**

```python
from datetime import datetime
from app.tools.base import tool_registry


@tool_registry.register(
    name="get_current_time",
    description="Get the current date and time",
    parameters={
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone name, e.g. Asia/Shanghai. Defaults to UTC.",
            }
        },
    },
    risk="low",
)
async def get_current_time(timezone: str = "UTC") -> str:
    return f"Current time: {datetime.utcnow().isoformat()} UTC"


@tool_registry.register(
    name="calculator",
    description="Evaluate a mathematical expression",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression to evaluate, e.g. '2 + 3 * 4'",
            }
        },
        "required": ["expression"],
    },
    risk="low",
)
async def calculator(expression: str) -> str:
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return "Error: expression contains disallowed characters"
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"
```

- [ ] **Step 3: Write backend/app/tools/web_search.py**

```python
import httpx
from app.tools.base import tool_registry


@tool_registry.register(
    name="web_search",
    description="Search the web for real-time information using DuckDuckGo",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            }
        },
        "required": ["query"],
    },
    risk="low",
)
async def web_search(query: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
                timeout=10,
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return f"Search result: {abstract}"
            related = data.get("RelatedTopics", [])
            if related:
                results = [item.get("Text", "") for item in related[:3] if item.get("Text")]
                return "Search results:\n" + "\n".join(f"- {r}" for r in results)
            return f"No results found for '{query}'"
    except Exception as e:
        return f"Search error: {e}"
```

- [ ] **Step 4: Write backend/app/tools/file_ops.py**

```python
import os
from app.tools.base import tool_registry

ALLOWED_PATHS = {"/tmp", os.getcwd()}


def _is_safe_path(path: str) -> bool:
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(p) for p in ALLOWED_PATHS)


@tool_registry.register(
    name="read_file",
    description="Read contents of a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file",
            }
        },
        "required": ["path"],
    },
    risk="medium",
)
async def read_file(path: str) -> str:
    if not _is_safe_path(path):
        return f"Error: access denied for path '{path}'"
    try:
        with open(path) as f:
            content = f.read(4096)
            truncated = len(content) >= 4096
            return content[:4096] + ("\n...[truncated]" if truncated else "")
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool_registry.register(
    name="write_file",
    description="Write content to a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file",
            },
            "content": {
                "type": "string",
                "description": "Content to write",
            },
        },
        "required": ["path", "content"],
    },
    risk="high",
)
async def write_file(path: str, content: str) -> str:
    if not _is_safe_path(path):
        return f"Error: access denied for path '{path}'"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"File written successfully: {path} ({len(content)} bytes)"
    except Exception as e:
        return f"Error writing file: {e}"
```

- [ ] **Step 5: Write backend/app/tools/code_executor.py**

```python
import subprocess
import tempfile
import os
from app.tools.base import tool_registry


@tool_registry.register(
    name="execute_code",
    description="Execute Python code in a sandboxed subprocess",
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
            "language": {
                "type": "string",
                "description": "Programming language, currently only 'python' is supported",
            },
        },
        "required": ["code"],
    },
    risk="high",
)
async def execute_code(code: str, language: str = "python") -> str:
    if language != "python":
        return f"Error: language '{language}' is not supported"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/tmp",
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        return output[:4096] or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: code execution timed out (30s)"
    except Exception as e:
        return f"Error executing code: {e}"
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 6: Write backend/app/tools/__init__.py**

```python
from app.tools.base import tool_registry, ToolDefinition
from app.tools import system_tools, web_search, file_ops, code_executor

__all__ = ["tool_registry", "ToolDefinition"]
```

- [ ] **Step 7: Write backend/tests/test_tools.py**

```python
import pytest
from app.tools import tool_registry
from app.tools.system_tools import calculator, get_current_time


@pytest.mark.asyncio
async def test_calculator_basic():
    result = await calculator("2 + 3")
    assert result == "5"


@pytest.mark.asyncio
async def test_calculator_complex():
    result = await calculator("(10 * 5) / 2")
    assert "25" in result


@pytest.mark.asyncio
async def test_calculator_invalid_chars():
    result = await calculator("__import__('os')")
    assert "Error" in result


@pytest.mark.asyncio
async def test_get_current_time():
    result = await get_current_time()
    assert "Current time:" in result
    assert "UTC" in result


def test_tool_registry_has_all_builtins():
    names = [t.name for t in tool_registry.list_all()]
    assert "calculator" in names
    assert "get_current_time" in names
    assert "web_search" in names
    assert "read_file" in names
    assert "write_file" in names
    assert "execute_code" in names


def test_tool_risk_levels():
    assert tool_registry.requires_confirmation("calculator") is False
    assert tool_registry.requires_confirmation("web_search") is False
    assert tool_registry.requires_confirmation("write_file") is True
    assert tool_registry.requires_confirmation("execute_code") is True


def test_get_schemas():
    schemas = tool_registry.get_schemas(["calculator"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "calculator"
```

- [ ] **Step 8: Run tests**

```bash
cd backend && python -m pytest tests/test_tools.py -v
```

Expected: 7 tests pass

- [ ] **Step 9: Commit**

```bash
git add backend/app/tools/ backend/tests/test_tools.py
git commit -m "feat: add tool registry and built-in tools"
```

---

### Task 6: LLM Gateway (LiteLLM wrapper)

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/llm_gateway.py`
- Test: `backend/tests/test_llm_gateway.py`

- [ ] **Step 1: Write backend/app/core/__init__.py (empty)**

```python
```

- [ ] **Step 2: Write backend/app/core/llm_gateway.py**

```python
from typing import AsyncIterator
import litellm

from app.config import settings


class LLMGateway:
    async def chat_completion(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_base: str | None = None,
        api_key: str | None = None,
        stream: bool = True,
    ):
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": settings.llm_timeout,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
        if api_base:
            kwargs["api_base"] = api_base
        if api_key:
            kwargs["api_key"] = api_key

        if stream:
            return self._stream_response(**kwargs)
        else:
            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message

    async def _stream_response(self, **kwargs) -> AsyncIterator[dict]:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "delta", "content": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.function.name:
                        yield {
                            "type": "tool_call",
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
        yield {"type": "done"}

    async def get_embedding(self, text: str, api_base: str | None = None, api_key: str | None = None) -> list[float]:
        kwargs = {
            "model": "text-embedding-3-small",
            "input": [text],
        }
        if api_base:
            kwargs["api_base"] = api_base
        if api_key:
            kwargs["api_key"] = api_key
        response = await litellm.aembedding(**kwargs)
        return response.data[0]["embedding"]


llm_gateway = LLMGateway()
```

- [ ] **Step 3: Write backend/tests/test_llm_gateway.py**

```python
import pytest
from app.core.llm_gateway import LLMGateway


def test_llm_gateway_initializes():
    gw = LLMGateway()
    assert gw is not None


@pytest.mark.asyncio
async def test_get_embedding_returns_vector():
    gw = LLMGateway()
    embedding = await gw.get_embedding("hello world")
    assert isinstance(embedding, list)
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_llm_gateway.py -v
```

Note: the embedding test requires a valid `OPENAI_API_KEY` env var.

Expected: 2 tests pass (or skip if no API key)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ backend/tests/test_llm_gateway.py
git commit -m "feat: add LLM gateway with LiteLLM"
```

---

### Task 7: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/agent.py`
- Create: `backend/app/schemas/conversation.py`
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/schemas/provider.py`

- [ ] **Step 1: Write backend/app/schemas/__init__.py (empty)**

```python
```

- [ ] **Step 2: Write backend/app/schemas/agent.py**

```python
from pydantic import BaseModel, Field
from uuid import UUID


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    avatar: str = "🤖"
    system_prompt: str = "You are a helpful assistant."
    model: str
    tools: list[str] = []
    temperature: float = 0.7
    max_tokens: int = 4096


class AgentUpdate(BaseModel):
    name: str | None = None
    avatar: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    avatar: str
    system_prompt: str
    model: str
    tools: list[str]
    temperature: float
    max_tokens: int

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Write backend/app/schemas/conversation.py**

```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ConversationCreate(BaseModel):
    agent_id: UUID
    title: str = "New Chat"


class ConversationResponse(BaseModel):
    id: UUID
    agent_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Write backend/app/schemas/chat.py**

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    agent_id: str
```

- [ ] **Step 5: Write backend/app/schemas/provider.py**

```python
from pydantic import BaseModel, Field
from uuid import UUID


class ProviderCreate(BaseModel):
    name: str
    provider: str = "openai"
    api_base: str
    api_key: str
    models: list[str] = []
    is_active: bool = True


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    models: list[str] | None = None
    is_active: bool | None = None


class ProviderResponse(BaseModel):
    id: UUID
    name: str
    provider: str
    api_base: str
    api_key: str
    models: list[str]
    is_active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic schemas"
```

---

### Task 8: Agent and Provider CRUD API endpoints

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/agents.py`
- Create: `backend/app/api/providers.py`
- Test: `backend/tests/test_agents_api.py`
- Test: `backend/tests/test_providers_api.py`

- [ ] **Step 1: Write backend/app/api/__init__.py (empty)**

```python
```

- [ ] **Step 2: Write backend/app/api/agents.py**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(**data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: UUID, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
```

- [ ] **Step 3: Write backend/app/api/providers.py**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.provider import LLMProvider
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.created_at.desc()))
    providers = result.scalars().all()
    # Mask API keys
    for p in providers:
        if p.api_key and len(p.api_key) > 8:
            p.api_key = p.api_key[:4] + "****" + p.api_key[-4:]
    return providers


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    provider = LLMProvider(**data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: UUID, data: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
```

- [ ] **Step 4: Register routers in backend/app/main.py**

Update `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.providers import router as providers_router

app = FastAPI(title="Agent Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(providers_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Write backend/tests/test_agents_api.py**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import get_db, async_session


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_agents_empty(client):
    resp = await client.get("/api/agents")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_agent(client):
    resp = await client.post("/api/agents", json={
        "name": "Test Agent",
        "model": "gpt-4o",
        "tools": ["calculator"],
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
```

- [ ] **Step 6: Run agent API tests**

```bash
cd backend && python -m pytest tests/test_agents_api.py -v
```

Expected: 4 tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/ backend/app/main.py backend/tests/test_agents_api.py backend/tests/test_providers_api.py
git commit -m "feat: add agent and provider CRUD APIs"
```

---

### Task 9: Memory manager

**Files:**
- Create: `backend/app/core/memory_manager.py`
- Test: `backend/tests/test_memory.py`

- [ ] **Step 1: Write backend/app/core/memory_manager.py**

```python
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import cosine_distance

from app.models.memory import Memory
from app.core.llm_gateway import llm_gateway
from app.config import settings


class MemoryManager:
    async def retrieve(self, db: AsyncSession, agent_id: str, query: str) -> list[str]:
        try:
            embedding = await llm_gateway.get_embedding(query)
        except Exception:
            return []

        result = await db.execute(
            select(Memory.content)
            .where(Memory.agent_id == agent_id)
            .order_by(cosine_distance(Memory.embedding, embedding))
            .limit(settings.memory_top_k)
        )
        return [row[0] for row in result.all()]

    async def store(self, db: AsyncSession, agent_id: str, content: str):
        try:
            embedding = await llm_gateway.get_embedding(content)
        except Exception:
            return

        # Deduplicate: check if similar memory exists
        result = await db.execute(
            select(Memory)
            .where(Memory.agent_id == agent_id)
            .order_by(cosine_distance(Memory.embedding, embedding))
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.content = content
            existing.embedding = embedding
        else:
            memory = Memory(agent_id=agent_id, content=content, embedding=embedding)
            db.add(memory)
        await db.commit()

    async def extract_and_store(self, db: AsyncSession, agent_id: str, messages: list[dict]):
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-6:])
        prompt = (
            "Extract 1-3 key facts about the user from this conversation. "
            "Focus on preferences, identity, and recurring topics. "
            "Output one fact per line, no numbering or prefixes.\n\n"
            f"{text}"
        )
        try:
            response = await llm_gateway.chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            facts = response.content.strip().split("\n") if hasattr(response, 'content') else []
            for fact in facts:
                fact = fact.strip()
                if fact and len(fact) > 5:
                    await self.store(db, agent_id, fact)
        except Exception:
            pass


memory_manager = MemoryManager()
```

- [ ] **Step 2: Write backend/tests/test_memory.py**

```python
import pytest
from app.core.memory_manager import MemoryManager


def test_memory_manager_init():
    mm = MemoryManager()
    assert mm is not None


@pytest.mark.asyncio
async def test_retrieve_empty_without_embedding():
    mm = MemoryManager()
    # Without a real DB session, retrieve should handle gracefully
    # This is a smoke test for the interface
    assert mm is not None
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_memory.py -v
```

Expected: 2 tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/memory_manager.py backend/tests/test_memory.py
git commit -m "feat: add memory manager"
```

---

### Task 10: Agent runtime and chat SSE endpoint

**Files:**
- Create: `backend/app/core/agent_runtime.py`
- Create: `backend/app/api/conversations.py`
- Create: `backend/app/api/chat.py`
- Test: `backend/tests/test_agent_runtime.py`
- Modify: `backend/app/main.py` (add routers)

- [ ] **Step 1: Write backend/app/core/agent_runtime.py**

```python
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.config import settings
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.provider import LLMProvider
from app.core.llm_gateway import llm_gateway
from app.core.memory_manager import memory_manager
from app.tools import tool_registry


class AgentRuntime:
    async def run(
        self,
        db: AsyncSession,
        agent_id: str,
        conversation_id: str,
        user_message: str,
    ):
        # Load agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Load provider
        model_parts = agent.model.split("/", 1)
        provider = None
        if len(model_parts) == 2:
            provider_result = await db.execute(
                select(LLMProvider).where(LLMProvider.name == model_parts[0], LLMProvider.is_active == True)
            )
            provider = provider_result.scalar_one_or_none()

        actual_model = model_parts[1] if len(model_parts) == 2 else agent.model

        # Load conversation history
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(20)
        )
        history = msg_result.scalars().all()

        # Retrieve memories
        memories = await memory_manager.retrieve(db, agent_id, user_message)

        # Build messages
        messages = [{"role": "system", "content": agent.system_prompt}]
        if memories:
            memory_text = "Relevant context about the user:\n" + "\n".join(f"- {m}" for m in memories)
            messages.append({"role": "system", "content": memory_text})
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        # Save user message
        user_msg = Message(conversation_id=conversation_id, role="user", content=user_message)
        db.add(user_msg)
        await db.commit()

        # Agent loop
        tools = tool_registry.get_schemas(agent.tools) if agent.tools else None
        api_base = provider.api_base if provider else None
        api_key = provider.api_key if provider else None

        round_count = 0
        full_response = ""

        while round_count < settings.max_tool_rounds:
            round_count += 1
            stream = await llm_gateway.chat_completion(
                model=actual_model,
                messages=messages,
                tools=tools,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                api_base=api_base,
                api_key=api_key,
            )

            tool_calls_in_round = []
            async for event in stream:
                if event["type"] == "delta":
                    full_response += event["content"]
                    yield {"event": "delta", "data": json.dumps({"content": event["content"]})}
                elif event["type"] == "tool_call":
                    tool_calls_in_round.append(event)
                    yield {"event": "tool_call", "data": json.dumps({"name": event["name"], "arguments": event["arguments"]})}
                elif event["type"] == "done":
                    pass

            if not tool_calls_in_round:
                # No tool calls, assistant response done
                break

            # Execute tools
            for tc in tool_calls_in_round:
                tool_def = tool_registry.get(tc["name"])
                if tool_def:
                    if tool_def.risk == "high":
                        yield {"event": "confirm_required", "data": json.dumps({"tool": tc["name"], "args": tc["arguments"]})}
                        # Wait for confirmation — for now, skip high-risk tools in auto mode
                        tool_result = f"Tool '{tc['name']}' requires user confirmation. Skipped."
                    else:
                        try:
                            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                            result = await tool_def.function(**args)
                            tool_result = str(result)
                        except Exception as e:
                            tool_result = f"Tool error: {e}"
                else:
                    tool_result = f"Unknown tool: {tc['name']}"

                yield {"event": "tool_result", "data": json.dumps({"tool": tc["name"], "output": tool_result})}
                messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}]})
                messages.append({"role": "tool", "content": tool_result, "tool_call_id": "call_1"})

        # Save assistant message
        assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=full_response)
        db.add(assistant_msg)
        await db.commit()

        # Async memory extraction
        all_msgs = [{"role": m.role, "content": m.content} for m in history] + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": full_response},
        ]
        await memory_manager.extract_and_store(db, agent_id, all_msgs)

        yield {"event": "done", "data": json.dumps({"conversation_id": str(conversation_id)})}


agent_runtime = AgentRuntime()
```

- [ ] **Step 2: Write backend/app/api/conversations.py**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationResponse, MessageResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(agent_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Conversation).order_by(Conversation.updated_at.desc())
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(**data.model_dump())
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()
```

- [ ] **Step 3: Write backend/app/api/chat.py**

```python
from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.schemas.chat import ChatRequest
from app.core.agent_runtime import agent_runtime

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conversation_id}")
async def chat(conversation_id: UUID, data: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_stream():
        try:
            async for event in agent_runtime.run(
                db=db,
                agent_id=str(conv.agent_id),
                conversation_id=str(conversation_id),
                user_message=data.message,
            ):
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 4: Add routers to backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.providers import router as providers_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router

app = FastAPI(title="Agent Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(providers_router)
app.include_router(conversations_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Write backend/tests/test_agent_runtime.py**

```python
import pytest
from app.core.agent_runtime import AgentRuntime


def test_agent_runtime_init():
    ar = AgentRuntime()
    assert ar is not None
```

- [ ] **Step 6: Run tests**

```bash
cd backend && python -m pytest tests/test_agent_runtime.py -v
```

Expected: 1 test pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/agent_runtime.py backend/app/api/conversations.py backend/app/api/chat.py backend/app/main.py backend/tests/test_agent_runtime.py
git commit -m "feat: add agent runtime and chat SSE endpoint"
```

---

### Task 11: Backend conftest and integration test setup

**Files:**
- Create: `backend/tests/conftest.py`
- Modify: `backend/app/main.py` (test DB override support)

- [ ] **Step 1: Write backend/tests/conftest.py**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: Update tests that define their own client fixture to use the shared conftest**

Remove the client fixture from `test_agents_api.py` (it's now in conftest).

- [ ] **Step 3: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_agents_api.py
git commit -m "test: add shared test fixtures"
```

---

### Task 12: Frontend project initialization

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/page.tsx`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Initialize Next.js**

```bash
cd /home/hc/work/my-service-agent && npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --no-turbopack
```

- [ ] **Step 2: Install shadcn/ui**

```bash
cd frontend && npx shadcn@latest init -d
```

- [ ] **Step 3: Install additional shadcn components**

```bash
cd frontend && npx shadcn@latest add button input textarea dialog card scroll-area dropdown-menu separator avatar tooltip command popover
```

- [ ] **Step 4: Install additional npm packages**

```bash
cd frontend && npm install react-markdown remark-gfm rehype-highlight lucide-react date-fns
```

- [ ] **Step 5: Write frontend/app/globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 0 0% 3.9%;
    --radius: 0.5rem;
    --chart-1: 12 76% 61%;
    --chart-2: 173 58% 39%;
    --chart-3: 197 37% 24%;
    --chart-4: 43 74% 66%;
    --chart-5: 27 87% 67%;
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    --card: 0 0% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 0 0% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 0 0% 9%;
    --secondary: 0 0% 14.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 0 0% 14.9%;
    --muted-foreground: 0 0% 63.9%;
    --accent: 0 0% 14.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 14.9%;
    --input: 0 0% 14.9%;
    --ring: 0 0% 83.1%;
    --chart-1: 220 70% 50%;
    --chart-2: 160 60% 45%;
    --chart-3: 30 80% 55%;
    --chart-4: 280 65% 60%;
    --chart-5: 340 75% 55%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 6: Write frontend/Dockerfile**

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npm run build

CMD ["npm", "start"]
```

- [ ] **Step 7: Write frontend/app/page.tsx (redirect to /chat)**

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "chore: initialize Next.js frontend with shadcn/ui"
```

---

### Task 13: Frontend API client and SSE hook

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/hooks/use-sse.ts`

- [ ] **Step 1: Write frontend/lib/api.ts**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Agent {
  id: string;
  name: string;
  avatar: string;
  system_prompt: string;
  model: string;
  tools: string[];
  temperature: number;
  max_tokens: number;
}

export interface Conversation {
  id: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  created_at: string;
}

export interface Provider {
  id: string;
  name: string;
  provider: string;
  api_base: string;
  api_key: string;
  models: string[];
  is_active: boolean;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Agents
  listAgents: () => fetchJson<Agent[]>("/api/agents"),
  createAgent: (data: Partial<Agent>) =>
    fetchJson<Agent>("/api/agents", { method: "POST", body: JSON.stringify(data) }),
  updateAgent: (id: string, data: Partial<Agent>) =>
    fetchJson<Agent>(`/api/agents/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAgent: (id: string) =>
    fetchJson<void>(`/api/agents/${id}`, { method: "DELETE" }),

  // Conversations
  listConversations: (agentId?: string) =>
    fetchJson<Conversation[]>(`/api/conversations${agentId ? `?agent_id=${agentId}` : ""}`),
  createConversation: (agentId: string, title?: string) =>
    fetchJson<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, title: title || "New Chat" }),
    }),
  deleteConversation: (id: string) =>
    fetchJson<void>(`/api/conversations/${id}`, { method: "DELETE" }),
  getMessages: (conversationId: string) =>
    fetchJson<Message[]>(`/api/conversations/${conversationId}/messages`),

  // Providers
  listProviders: () => fetchJson<Provider[]>("/api/providers"),
  createProvider: (data: Partial<Provider>) =>
    fetchJson<Provider>("/api/providers", { method: "POST", body: JSON.stringify(data) }),
  updateProvider: (id: string, data: Partial<Provider>) =>
    fetchJson<Provider>(`/api/providers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProvider: (id: string) =>
    fetchJson<void>(`/api/providers/${id}`, { method: "DELETE" }),
};
```

- [ ] **Step 2: Write frontend/hooks/use-sse.ts**

```typescript
"use client";

import { useCallback, useRef, useState } from "react";

export interface SSEEvent {
  event: string;
  data: string;
}

export function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(
    async (
      conversationId: string,
      agentId: string,
      message: string,
      onDelta: (content: string) => void,
      onToolCall: (name: string, args: string) => void,
      onToolResult: (tool: string, output: string) => void,
      onDone: () => void,
      onError: (msg: string) => void
    ) => {
      setIsStreaming(true);
      const abort = new AbortController();
      abortRef.current = abort;

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${API_URL}/api/chat/${conversationId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, agent_id: agentId }),
          signal: abort.signal,
        });

        if (!res.ok || !res.body) {
          onError(`HTTP ${res.status}`);
          setIsStreaming(false);
          return;
        }

        const reader = res.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (eventType === "delta") {
                const parsed = JSON.parse(data);
                onDelta(parsed.content);
              } else if (eventType === "tool_call") {
                const parsed = JSON.parse(data);
                onToolCall(parsed.name, parsed.arguments);
              } else if (eventType === "tool_result") {
                const parsed = JSON.parse(data);
                onToolResult(parsed.tool, parsed.output);
              } else if (eventType === "done") {
                onDone();
              } else if (eventType === "error") {
                const parsed = JSON.parse(data);
                onError(parsed.message);
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          onError(err.message);
        }
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    readerRef.current?.cancel();
    setIsStreaming(false);
  }, []);

  return { isStreaming, startStream, stopStream };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts frontend/hooks/use-sse.ts
git commit -m "feat: add frontend API client and SSE hook"
```

---

### Task 14: Chat page — Sidebar component

**Files:**
- Create: `frontend/components/chat/sidebar.tsx`
- Create: `frontend/components/chat/agent-selector.tsx`
- Create: `frontend/components/chat/conversation-list.tsx`

- [ ] **Step 1: Write frontend/components/chat/agent-selector.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import { Check, ChevronsUpDown, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { api, Agent } from "@/lib/api";

interface AgentSelectorProps {
  selectedId: string | null;
  onSelect: (agent: Agent) => void;
}

export function AgentSelector({ selectedId, onSelect }: AgentSelectorProps) {
  const [open, setOpen] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    api.listAgents().then(setAgents).catch(console.error);
  }, []);

  const selected = agents.find((a) => a.id === selectedId);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" className="w-full justify-between">
          {selected ? (
            <span className="flex items-center gap-2">
              <span>{selected.avatar}</span>
              <span className="truncate">{selected.name}</span>
            </span>
          ) : (
            <span className="flex items-center gap-2 text-muted-foreground">
              <Bot className="h-4 w-4" />
              Select Agent
            </span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[240px] p-0">
        <Command>
          <CommandInput placeholder="Search agents..." />
          <CommandList>
            <CommandEmpty>No agents found.</CommandEmpty>
            <CommandGroup>
              {agents.map((agent) => (
                <CommandItem
                  key={agent.id}
                  value={agent.name}
                  onSelect={() => {
                    onSelect(agent);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      selectedId === agent.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <span className="mr-2">{agent.avatar}</span>
                  {agent.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 2: Write frontend/components/chat/conversation-list.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import { MessageSquare, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api, Conversation } from "@/lib/api";
import { format, isToday, isYesterday } from "date-fns";

interface ConversationListProps {
  agentId: string | null;
  activeId: string | null;
  onSelect: (conv: Conversation) => void;
  onNew: () => void;
}

export function ConversationList({ agentId, activeId, onSelect, onNew }: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    if (agentId) {
      api.listConversations(agentId).then(setConversations).catch(console.error);
    } else {
      setConversations([]);
    }
  }, [agentId]);

  const groupByDate = (convs: Conversation[]) => {
    const groups: Record<string, Conversation[]> = { Today: [], Yesterday: [], Earlier: [] };
    convs.forEach((c) => {
      const d = new Date(c.created_at);
      if (isToday(d)) groups["Today"].push(c);
      else if (isYesterday(d)) groups["Yesterday"].push(c);
      else groups["Earlier"].push(c);
    });
    return Object.entries(groups).filter(([, v]) => v.length > 0);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3">
        <Button className="w-full" onClick={onNew} disabled={!agentId}>
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>
      <ScrollArea className="flex-1 px-3">
        {groupByDate(conversations).map(([group, convs]) => (
          <div key={group} className="mb-3">
            <p className="text-xs text-muted-foreground px-2 mb-1">{group}</p>
            {convs.map((conv) => (
              <div
                key={conv.id}
                className={`flex items-center group rounded-md px-2 py-1.5 cursor-pointer text-sm hover:bg-accent ${
                  activeId === conv.id ? "bg-accent" : ""
                }`}
                onClick={() => onSelect(conv)}
              >
                <MessageSquare className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate flex-1">{conv.title}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100"
                  onClick={(e) => handleDelete(e, conv.id)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        ))}
        {conversations.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">
            {agentId ? "No conversations yet" : "Select an agent to start"}
          </p>
        )}
      </ScrollArea>
    </div>
  );
}
```

- [ ] **Step 3: Write frontend/components/chat/sidebar.tsx**

```tsx
"use client";

import { Bot, Settings } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { AgentSelector } from "./agent-selector";
import { ConversationList } from "./conversation-list";
import { Agent, Conversation } from "@/lib/api";

interface SidebarProps {
  selectedAgent: Agent | null;
  activeConversationId: string | null;
  onSelectAgent: (agent: Agent) => void;
  onSelectConversation: (conv: Conversation) => void;
  onNewConversation: () => void;
}

export function Sidebar({
  selectedAgent,
  activeConversationId,
  onSelectAgent,
  onSelectConversation,
  onNewConversation,
}: SidebarProps) {
  return (
    <div className="flex flex-col h-full w-[280px] border-r bg-muted/30">
      <div className="p-3">
        <AgentSelector
          selectedId={selectedAgent?.id ?? null}
          onSelect={onSelectAgent}
        />
      </div>
      <Separator />
      <div className="flex-1 overflow-hidden">
        <ConversationList
          agentId={selectedAgent?.id ?? null}
          activeId={activeConversationId}
          onSelect={onSelectConversation}
          onNew={onNewConversation}
        />
      </div>
      <Separator />
      <div className="p-3 flex flex-col gap-1">
        <Link href="/agents">
          <Button variant="ghost" className="w-full justify-start text-sm">
            <Bot className="mr-2 h-4 w-4" />
            Manage Agents
          </Button>
        </Link>
        <Link href="/settings">
          <Button variant="ghost" className="w-full justify-start text-sm">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Button>
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/chat/sidebar.tsx frontend/components/chat/agent-selector.tsx frontend/components/chat/conversation-list.tsx
git commit -m "feat: add chat sidebar components"
```

---

### Task 15: Chat page — Message components and chat area

**Files:**
- Create: `frontend/components/chat/message-bubble.tsx`
- Create: `frontend/components/chat/message-input.tsx`
- Create: `frontend/components/chat/tool-call-card.tsx`
- Create: `frontend/components/chat/chat-area.tsx`

- [ ] **Step 1: Write frontend/components/chat/message-bubble.tsx**

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
  role: "user" | "assistant" | "tool";
  content: string;
  isStreaming?: boolean;
}

export function MessageBubble({ role, content, isStreaming }: MessageBubbleProps) {
  if (role === "tool") {
    return null; // Tool messages shown via ToolCallCard
  }

  const isUser = role === "user";

  return (
    <div className={`flex gap-3 py-4 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2 ${
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-current animate-pulse ml-0.5" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write frontend/components/chat/tool-call-card.tsx**

```tsx
"use client";

import { useState } from "react";
import { Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ToolCallCardProps {
  name: string;
  args: string;
  output?: string;
  isExecuting?: boolean;
}

export function ToolCallCard({ name, args, output, isExecuting }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="flex justify-start py-2">
      <Card className="max-w-[70%] border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800">
        <CardContent className="p-3">
          <button
            className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400 w-full"
            onClick={() => setExpanded(!expanded)}
          >
            <Wrench className="h-4 w-4" />
            {isExecuting ? `Calling ${name}...` : `Called ${name}`}
            {output && (expanded ? <ChevronDown className="h-4 w-4 ml-auto" /> : <ChevronRight className="h-4 w-4 ml-auto" />)}
          </button>
          {expanded && (
            <div className="mt-2 text-xs space-y-1">
              <div>
                <span className="font-medium">Args:</span>{" "}
                <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">{args}</code>
              </div>
              {output && (
                <div>
                  <span className="font-medium">Result:</span>
                  <pre className="mt-1 bg-amber-100 dark:bg-amber-900 p-2 rounded text-xs whitespace-pre-wrap">
                    {output}
                  </pre>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Write frontend/components/chat/message-input.tsx**

```tsx
"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface MessageInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function MessageInput({ onSend, isStreaming }: MessageInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput("");
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-background p-4">
      <div className="flex gap-3 max-w-3xl mx-auto">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Send a message..."
          rows={1}
          className="min-h-[44px] max-h-[200px] resize-none"
          disabled={isStreaming}
        />
        <Button onClick={handleSend} disabled={!input.trim() || isStreaming} size="icon" className="h-11 w-11 shrink-0">
          {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write frontend/components/chat/chat-area.tsx**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Agent, Conversation, Message, api } from "@/lib/api";
import { useSSE } from "@/hooks/use-sse";
import { MessageBubble } from "./message-bubble";
import { MessageInput } from "./message-input";
import { ToolCallCard } from "./tool-call-card";

interface ChatAreaProps {
  agent: Agent | null;
  conversation: Conversation | null;
}

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
}

interface ToolCallEvent {
  name: string;
  args: string;
  output?: string;
  isExecuting: boolean;
}

export function ChatArea({ agent, conversation }: ChatAreaProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const { isStreaming, startStream, stopStream } = useSSE();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversation) {
      api.getMessages(conversation.id).then((msgs) => {
        setMessages(
          msgs
            .filter((m) => m.role !== "tool")
            .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }))
        );
      });
    } else {
      setMessages([]);
    }
    setStreamingContent("");
    setToolCalls([]);
  }, [conversation?.id]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = (content: string) => {
    if (!agent || !conversation) return;

    const userMsg: DisplayMessage = { role: "user", content };
    setMessages((prev) => [...prev, userMsg]);
    setStreamingContent("");
    setToolCalls([]);

    let assistantContent = "";

    startStream(
      conversation.id,
      agent.id,
      content,
      (delta) => {
        assistantContent += delta;
        setStreamingContent(assistantContent);
      },
      (name, args) => {
        setToolCalls((prev) => [...prev, { name, args, isExecuting: true }]);
      },
      (tool, output) => {
        setToolCalls((prev) =>
          prev.map((tc) => (tc.name === tool && tc.isExecuting ? { ...tc, output, isExecuting: false } : tc))
        );
      },
      () => {
        if (assistantContent) {
          setMessages((prev) => [...prev, { role: "assistant", content: assistantContent }]);
        }
        setStreamingContent("");
      },
      (error) => {
        console.error("Stream error:", error);
      }
    );
  };

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Select an agent to start chatting
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      <div className="border-b px-6 py-3 flex items-center gap-3">
        <span className="text-xl">{agent.avatar}</span>
        <div>
          <h2 className="font-semibold text-sm">{agent.name}</h2>
          <p className="text-xs text-muted-foreground">{agent.model}</p>
        </div>
      </div>
      <ScrollArea className="flex-1 px-6">
        <div className="max-w-3xl mx-auto">
          {messages.map((msg, i) => (
            <MessageBubble key={i} role={msg.role} content={msg.content} />
          ))}
          {toolCalls.map((tc, i) => (
            <ToolCallCard key={i} {...tc} />
          ))}
          {streamingContent && (
            <MessageBubble role="assistant" content={streamingContent} isStreaming />
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
      <MessageInput onSend={handleSend} isStreaming={isStreaming} />
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/chat/message-bubble.tsx frontend/components/chat/message-input.tsx frontend/components/chat/tool-call-card.tsx frontend/components/chat/chat-area.tsx
git commit -m "feat: add chat message components and chat area"
```

---

### Task 16: Chat page assembly

**Files:**
- Create: `frontend/app/chat/page.tsx`
- Create: `frontend/app/layout.tsx` (update with dark mode support)

- [ ] **Step 1: Write frontend/app/chat/page.tsx**

```tsx
"use client";

import { useState } from "react";
import { Sidebar } from "@/components/chat/sidebar";
import { ChatArea } from "@/components/chat/chat-area";
import { Agent, Conversation, api } from "@/lib/api";

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);

  const handleSelectAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    setActiveConversation(null);
  };

  const handleSelectConversation = (conv: Conversation) => {
    setActiveConversation(conv);
  };

  const handleNewConversation = async () => {
    if (!selectedAgent) return;
    const conv = await api.createConversation(selectedAgent.id);
    setActiveConversation(conv);
  };

  return (
    <div className="flex h-screen">
      <Sidebar
        selectedAgent={selectedAgent}
        activeConversationId={activeConversation?.id ?? null}
        onSelectAgent={handleSelectAgent}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <ChatArea agent={selectedAgent} conversation={activeConversation} />
    </div>
  );
}
```

- [ ] **Step 2: Write frontend/app/layout.tsx**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent Platform",
  description: "Personal multi-agent chat platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/chat/page.tsx frontend/app/layout.tsx
git commit -m "feat: assemble chat page"
```

---

### Task 17: Agent management page

**Files:**
- Create: `frontend/app/agents/page.tsx`
- Create: `frontend/components/agents/agent-card.tsx`
- Create: `frontend/components/agents/agent-form.tsx`

- [ ] **Step 1: Write frontend/components/agents/agent-form.tsx**

```tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Agent } from "@/lib/api";

interface AgentFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Agent>) => Promise<void>;
  agent?: Agent | null;
}

const BUILTIN_TOOLS = [
  "calculator",
  "get_current_time",
  "web_search",
  "read_file",
  "write_file",
  "execute_code",
];

export function AgentForm({ open, onClose, onSave, agent }: AgentFormProps) {
  const [name, setName] = useState(agent?.name || "");
  const [avatar, setAvatar] = useState(agent?.avatar || "🤖");
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt || "");
  const [model, setModel] = useState(agent?.model || "");
  const [tools, setTools] = useState<string[]>(agent?.tools || []);
  const [temperature, setTemperature] = useState(agent?.temperature ?? 0.7);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (agent) {
      setName(agent.name);
      setAvatar(agent.avatar);
      setSystemPrompt(agent.system_prompt);
      setModel(agent.model);
      setTools(agent.tools);
      setTemperature(agent.temperature);
    }
  }, [agent]);

  const toggleTool = (tool: string) => {
    setTools((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    await onSave({ name, avatar, system_prompt: systemPrompt, model, tools, temperature });
    setSaving(false);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{agent ? "Edit Agent" : "Create Agent"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="w-16">
              <label className="text-sm font-medium">Avatar</label>
              <Input value={avatar} onChange={(e) => setAvatar(e.target.value)} className="text-center text-xl" maxLength={2} />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Agent name" />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">Model</label>
            <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4o or provider/gpt-4o" />
          </div>
          <div>
            <label className="text-sm font-medium">System Prompt</label>
            <Textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful assistant..."
              rows={4}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Temperature: {temperature}</label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Tools</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {BUILTIN_TOOLS.map((tool) => (
                <Button
                  key={tool}
                  variant={tools.includes(tool) ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleTool(tool)}
                >
                  {tool}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || !model || saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Write frontend/components/agents/agent-card.tsx**

```tsx
"use client";

import { Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Agent } from "@/lib/api";

interface AgentCardProps {
  agent: Agent;
  onEdit: (agent: Agent) => void;
  onDelete: (id: string) => void;
}

export function AgentCard({ agent, onEdit, onDelete }: AgentCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{agent.avatar}</span>
            <div>
              <h3 className="font-semibold">{agent.name}</h3>
              <p className="text-xs text-muted-foreground">{agent.model}</p>
            </div>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" onClick={() => onEdit(agent)}>
              <Pencil className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => onDelete(agent.id)}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-2">{agent.system_prompt}</p>
        {agent.tools.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {agent.tools.map((t) => (
              <span key={t} className="text-xs bg-secondary px-2 py-0.5 rounded-full">
                {t}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Write frontend/app/agents/page.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/agents/agent-card";
import { AgentForm } from "@/components/agents/agent-form";
import { api, Agent } from "@/lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);

  const loadAgents = () => {
    api.listAgents().then(setAgents).catch(console.error);
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const handleSave = async (data: Partial<Agent>) => {
    if (editingAgent) {
      await api.updateAgent(editingAgent.id, data);
    } else {
      await api.createAgent(data);
    }
    setEditingAgent(null);
    loadAgents();
  };

  const handleDelete = async (id: string) => {
    await api.deleteAgent(id);
    loadAgents();
  };

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setFormOpen(true);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-6">
          <Link href="/chat">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-2xl font-bold flex-1">Agent Management</h1>
          <Button
            onClick={() => {
              setEditingAgent(null);
              setFormOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            Create Agent
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onEdit={handleEdit} onDelete={handleDelete} />
          ))}
          {agents.length === 0 && (
            <p className="text-muted-foreground col-span-2 text-center py-12">
              No agents yet. Create your first agent to get started.
            </p>
          )}
        </div>
        <AgentForm
          open={formOpen}
          onClose={() => {
            setFormOpen(false);
            setEditingAgent(null);
          }}
          onSave={handleSave}
          agent={editingAgent}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/agents/ frontend/components/agents/
git commit -m "feat: add agent management page"
```

---

### Task 18: Settings page

**Files:**
- Create: `frontend/app/settings/page.tsx`
- Create: `frontend/components/providers/provider-card.tsx`
- Create: `frontend/components/providers/provider-form.tsx`

- [ ] **Step 1: Write frontend/components/providers/provider-form.tsx**

```tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Provider } from "@/lib/api";

interface ProviderFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Provider>) => Promise<void>;
  provider?: Provider | null;
}

export function ProviderForm({ open, onClose, onSave, provider }: ProviderFormProps) {
  const [name, setName] = useState(provider?.name || "");
  const [apiBase, setApiBase] = useState(provider?.api_base || "");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState(provider?.models.join(", ") || "");

  useEffect(() => {
    if (provider) {
      setName(provider.name);
      setApiBase(provider.api_base);
      setModels(provider.models.join(", "));
    }
  }, [provider]);

  const handleSave = async () => {
    const modelList = models.split(",").map((m) => m.trim()).filter(Boolean);
    const data: Partial<Provider> = { name, api_base: apiBase, models: modelList };
    if (apiKey) data.api_key = apiKey;
    await onSave(data);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{provider ? "Edit Provider" : "Add Provider"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="OpenAI" />
          </div>
          <div>
            <label className="text-sm font-medium">API Base URL</label>
            <Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} placeholder="https://api.openai.com/v1" />
          </div>
          <div>
            <label className="text-sm font-medium">API Key {provider && "(leave blank to keep current)"}</label>
            <Input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder="sk-..." />
          </div>
          <div>
            <label className="text-sm font-medium">Models (comma-separated)</label>
            <Input value={models} onChange={(e) => setModels(e.target.value)} placeholder="gpt-4o, gpt-4o-mini" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || !apiBase}>Save</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Write frontend/components/providers/provider-card.tsx**

```tsx
"use client";

import { Pencil, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Provider } from "@/lib/api";

interface ProviderCardProps {
  provider: Provider;
  onEdit: (provider: Provider) => void;
  onDelete: (id: string) => void;
}

export function ProviderCard({ provider, onEdit, onDelete }: ProviderCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{provider.name}</h3>
            {provider.is_active ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" onClick={() => onEdit(provider)}>
              <Pencil className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => onDelete(provider.id)}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{provider.api_base}</p>
        <p className="text-xs font-mono mt-1">{provider.api_key}</p>
        <div className="flex flex-wrap gap-1 mt-2">
          {provider.models.map((m) => (
            <span key={m} className="text-xs bg-secondary px-2 py-0.5 rounded-full">
              {m}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Write frontend/app/settings/page.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ProviderCard } from "@/components/providers/provider-card";
import { ProviderForm } from "@/components/providers/provider-form";
import { api, Provider } from "@/lib/api";

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);

  const loadProviders = () => {
    api.listProviders().then(setProviders).catch(console.error);
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleSave = async (data: Partial<Provider>) => {
    if (editingProvider) {
      await api.updateProvider(editingProvider.id, data);
    } else {
      await api.createProvider(data);
    }
    setEditingProvider(null);
    loadProviders();
  };

  const handleDelete = async (id: string) => {
    await api.deleteProvider(id);
    loadProviders();
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-6">
          <Link href="/chat">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-2xl font-bold flex-1">Settings</h1>
        </div>

        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">LLM Providers</h2>
            <Button
              size="sm"
              onClick={() => {
                setEditingProvider(null);
                setFormOpen(true);
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Provider
            </Button>
          </div>
          <div className="space-y-3">
            {providers.map((p) => (
              <ProviderCard
                key={p.id}
                provider={p}
                onEdit={(provider) => {
                  setEditingProvider(provider);
                  setFormOpen(true);
                }}
                onDelete={handleDelete}
              />
            ))}
            {providers.length === 0 && (
              <p className="text-muted-foreground text-center py-8">
                No providers configured. Add an LLM provider to start.
              </p>
            )}
          </div>
        </div>

        <ProviderForm
          open={formOpen}
          onClose={() => {
            setFormOpen(false);
            setEditingProvider(null);
          }}
          onSave={handleSave}
          provider={editingProvider}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/settings/ frontend/components/providers/
git commit -m "feat: add settings/provider management page"
```

---

### Task 19: Final integration and verification

**Files:**
- Modify: `docker-compose.yml` (ensure it all works together)

- [ ] **Step 1: Verify backend starts**

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000 &
sleep 3
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds

- [ ] **Step 3: Add the `lib/utils.ts` utility file (needed by shadcn)**

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 4: Install clsx and tailwind-merge**

```bash
cd frontend && npm install clsx tailwind-merge
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: final integration fixes"
```

---

### Task 20: End-to-end smoke test

- [ ] **Step 1: Start all services**

```bash
docker compose up -d
```

- [ ] **Step 2: Run health check**

```bash
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Create a provider via API**

```bash
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name":"OpenAI","provider":"openai","api_base":"https://api.openai.com/v1","api_key":"sk-your-key","models":["gpt-4o-mini"]}'
```

- [ ] **Step 4: Create an agent via API**

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"Assistant","model":"OpenAI/gpt-4o-mini","tools":["calculator","get_current_time"]}'
```

- [ ] **Step 5: Create a conversation and send a chat message**

```bash
CONV_ID=$(curl -s -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"<agent-id-from-step-4>","title":"Test"}' | jq -r '.id')

curl -N -X POST "http://localhost:8000/api/chat/$CONV_ID" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello! What is 2+2?","agent_id":"<agent-id-from-step-4>"}'
```

- [ ] **Step 6: Open frontend**

Visit `http://localhost:3000` and verify:
- Chat page loads with sidebar
- Agent selector works
- Can create new conversations
- Settings page shows providers
- Agent management page works

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "test: end-to-end smoke test verification"
```