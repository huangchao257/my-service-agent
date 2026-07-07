# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

my-service-agent — 个人多 Agent 聊天平台。后端 FastAPI + litellm，前端 Next.js 16 + shadcn/ui，PostgreSQL + Redis 存储。

## 常用命令

```bash
# 开发环境启动（需先启动 Docker PostgreSQL/Redis）
make dev-backend      # 后端: uvicorn app.main:app --reload --port 8000
make dev-frontend     # 前端: next dev (Turbopack, 端口 3000)
make test             # 运行所有测试: cd backend && pytest -v

# 前端
cd frontend && npm run dev      # 启动开发服务器
cd frontend && npm run build    # 生产构建
cd frontend && npm run lint     # ESLint

# Docker 基础设施
docker compose up -d db         # 仅启动 PostgreSQL
# 当前使用本机 Docker 的 postgres/redis 容器，配置见 backend/.env
```

## 架构

### 后端 (backend/)

**分层结构：**
- `app/api/` — FastAPI 路由层（8 个模块: agents/providers/conversations/chat/mcp_servers/skills/memories/llm_interactions）
- `app/core/` — 核心引擎: `agent_runtime.py`（对话编排）、`llm_gateway.py`（litellm 封装+重试+token统计）、`memory_manager.py`（嵌入+余弦检索）、`mcp_manager.py`（MCP 工具聚合，mcp 库可选）、`cache.py`（Redis+内存降级）、`rate_limit.py`（令牌桶限流）、`crypto.py`（Fernet 静态加密）、`logging.py`（结构化 JSON 日志）
- `app/models/` — SQLAlchemy ORM 模型（8 个表: agents/providers/conversations/messages/memories/mcp_servers/skills/llm_interactions）
- `app/schemas/` — Pydantic 请求/响应模型
- `app/tools/` — 内置工具注册中心（6 个工具: calculator/get_current_time/web_search/read_file/write_file/execute_code）
- `app/database.py` — 异步 SQLAlchemy 引擎，`get_db()` 依赖注入，启动时 `create_all()`
- `app/config.py` — pydantic-settings，从 `.env` 加载，支持 DATABASE_URL/REDIS_URL/LLM_TIMEOUT/LLM_MAX_RETRIES/TOOL_TIMEOUT/ENCRYPTION_KEY 等

**关键设计约定：**
- **Agent.model 格式**：`"provider名称/model名称"`（如 `"zmn/gpt-4o"`），运行时分两段解析：provider 名称 → LLMProvider 记录取 api_base/api_key，model 名称前拼上 provider 类型作为 litellm 模型标识
- **Agent 高风险工具白名单**：`high_risk_tools_enabled` 列出已授权的 high risk 工具；未授权的高风险工具触发 `confirmation_required` SSE 事件并被跳过
- **Agent 可配置上下文**：`history_limit`（每轮注入历史条数，默认 20）、`memory_top_k`（记忆检索条数，None 用全局默认）
- **Skill 注入**：Agent.skills（技能名称列表）对应的 prompt_template 追加到 system message
- **MCP 接入**：Agent.mcp_servers（名称列表）→ mcp_manager 拉取工具 schema 合并进 tools；工具调用时内置工具未命中则分发到 MCP
- **工具调用循环**：agent_runtime 最多 `max_tool_rounds`（默认 10）轮，每轮流式调用 LLM → 检测 tool_calls → 执行工具（`asyncio.wait_for` 超时保护）→ 结果注入消息列表再调 LLM
- **工具调用唯一 ID**：`call_{round}_{index}` 防止跨轮次模型混淆
- **工具结果截断**：2000 字符，防止模型死循环
- **记忆存储**：余弦相似度去重（阈值 0.95），暴力搜索（无向量数据库），每次对话后 LLM 提取 1-3 条；`retrieve(top_k=...)` 可覆盖全局 top_k
- **LLM 重试**：瞬态错误（超时/429/5xx）指数退避重试，最多 `llm_max_retries` 次
- **LLM 交互记录**：messages_json 是完整上下文快照，token_usage_json 记录 token 用量；仅当 db/agent_id 参数传入时才记录
- **API Key 加密**：配置 `ENCRYPTION_KEY`（Fernet 密钥）后落库前加密，运行期 decrypt；未配置则明文（向后兼容）
- **限流**：进程内令牌桶，仅作用于 `/api/chat`（每 IP 60s 30 次）
- **标题生成**：首次对话自动用 Agent 配置的模型生成（prompt 要求跟随用户语言、最多 5 词）

**API 路由前缀：**
- `/api/agents` / `/api/providers` / `/api/conversations` — CRUD + GET 单条
- `/api/agents/{id}/duplicate` — 复制 Agent
- `/api/providers/{id}/test` | `/refresh-models` — 连通性测试 / 拉取模型列表
- `/api/conversations/{id}/export?format=markdown|json` — 导出会话
- `/api/chat/{conversation_id}` — POST，SSE 流式事件：delta → tool_call → tool_result → confirmation_required → title_updated → done(含 token_usage) → error
- `/api/chat/{conversation_id}/regenerate` — POST，删除末尾消息后用原 user 文本重跑
- `/api/memories` — GET 列表（支持 search 关键词）+ DELETE 单条
- `/api/llm-interactions` — GET 分页列表 + GET 详情
- `/api/mcp-servers` / `/api/skills` — CRUD + GET 单条
- `/api/providers/models` — 汇总所有已激活 Provider 的模型列表（带缓存）
- `/api/health` | `/api/health/deep` — 轻量 / 深度（DB+缓存）健康检查

### 前端 (frontend/)

- **框架**：Next.js 16 (App Router) + React 19 + TypeScript
- **UI**：shadcn/ui 组件 + Tailwind CSS 4 + `tw-animate-css`
- **聊天 SSE**：`hooks/use-sse.ts` 解析 SSE 事件流，通过 `activeConvRef` 防止切换会话时串扰
- **Markdown 渲染**：react-markdown + remark-gfm + rehype-highlight
- **路由**：`/chat?conv=<id>` 支持 URL 书签跳转；`/agents` / `/settings` / `/memories` / `/llm-interactions` 管理页面

### 测试 (backend/tests/)

- 使用 tempfile SQLite 保证每个测试干净隔离
- `conftest.py`：`db` fixture 替换 FastAPI 的 `get_db` 依赖为临时 SQLite；`client` fixture 提供 httpx AsyncClient；`db_session` fixture 直接给 ORM session；`autouse` 重置 cache/rate_limiter 全局单例
- 运行方式：`cd backend && pytest -v`（需先 `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest pytest-asyncio`）

### 基础设施

- **数据库**：本机 Docker PostgreSQL 18 + Redis 7，连接信息见 `backend/.env`
- **Docker Compose**：`docker-compose.yml` 定义 pgvector/pgvector:pg16 的 db 服务 + backend + frontend 构建
- **ORM 迁移**：alembic 目录已初始化但未实际使用（当前依赖 `create_all` 自动建表）