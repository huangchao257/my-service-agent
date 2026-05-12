# Agent Platform Design

## Overview

Personal multi-agent chat platform with tool-use and long-term memory, inspired by Doubao's chat interface.

## Requirements

- **Multi-agent**: Create and switch between multiple agents, each with custom system prompts and tool sets
- **Chat**: Real-time streaming conversation with Markdown rendering
- **Tool use**: Agents can call tools (web search, file I/O, code execution, etc.)
- **Memory**: Long-term semantic memory via vector search
- **Multi-provider**: Support OpenAI, Anthropic, and OpenAI-compatible APIs
- **Reference UI**: Doubao-style layout (left sidebar + main chat area)

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router) |
| UI | shadcn/ui + TailwindCSS |
| Backend | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 + Alembic |
| LLM Gateway | LiteLLM |
| Vector Store | pgvector |
| Streaming | SSE |
| Deployment | Docker Compose |

## Architecture

```
Frontend (Next.js)          Backend (FastAPI)           Data
─────────────                ────────────────           ────
Chat Page                    Chat API (SSE)             PostgreSQL
Agent Management             Agent CRUD                 pgvector
Settings                     Provider CRUD
                             Agent Runtime
                               ├─ Memory Retrieval
                               ├─ Tool Executor
                               └─ LLM Call (LiteLLM)
```

### Agent Runtime Loop

1. Load context: recent N messages + retrieved long-term memories
2. Build prompt: system_prompt + memories + history + user_message
3. Call LLM via LiteLLM
4. If tool_call → execute tool → feed result back → goto 3 (max 10 rounds)
5. If text → stream to frontend via SSE
6. Save messages to DB
7. Async: extract memories, embed, upsert to pgvector

### Safety

- High-risk tools (write_file, execute_code) require user confirmation in frontend
- execute_code runs in Docker sandbox
- Tool execution timeout: 30s per tool call
- LLM call timeout: 60s; total conversation timeout: 300s

## Data Models

```
Agent: id, name, avatar, system_prompt, model, tools[JSON], temperature, max_tokens, created_at, updated_at
Conversation: id, agent_id, title, created_at, updated_at
Message: id, conversation_id, role(user/assistant/tool), content, created_at
Memory: id, agent_id, content, embedding(pgvector 1536d), created_at
LLMProvider: id, name, provider(openai/anthropic/compatible), api_base, api_key(encrypted), models[JSON], is_active
```

## API Endpoints

```
POST   /api/chat/{conversation_id}     → SSE stream
GET    /api/conversations               → List conversations
POST   /api/conversations               → Create conversation
DELETE /api/conversations/{id}          → Delete conversation
GET    /api/conversations/{id}/messages → Message history

GET    /api/agents                      → List agents
POST   /api/agents                      → Create agent
PUT    /api/agents/{id}                 → Update agent
DELETE /api/agents/{id}                 → Delete agent

GET    /api/providers                   → List providers
POST   /api/providers                   → Add provider
PUT    /api/providers/{id}              → Update provider
DELETE /api/providers/{id}              → Delete provider
```

### SSE Events

```
event: delta        data: {"content": "..."}
event: tool_call    data: {"name": "...", "args": {...}}
event: tool_result  data: {"output": "..."}
event: done         data: {"conversation_id": "..."}
event: error        data: {"message": "..."}
```

## Pages

1. **`/chat`** — Main chat page
   - Left sidebar: agent selector, new-chat button, conversation list (grouped by date)
   - Chat area: agent header, message bubbles (Markdown + code highlighting), streaming animation
   - Input: textarea with tool/system buttons, Shift+Enter newline, Enter send
   - Tool call progress shown as collapsible cards
   - Responsive sidebar (collapsible on small screens)
   - Dark mode via system preference

2. **`/agents`** — Agent management
   - Grid of agent cards with name, model, system prompt preview, tools
   - Create/edit/delete with form dialog

3. **`/settings`** — Provider configuration
   - List of configured LLM providers with masked API keys
   - Add/edit/delete with form dialog

## Built-in Tools

| Tool | Description | Risk |
|------|-------------|------|
| web_search | Internet search | Low |
| read_file | Read local files | Medium (path restriction) |
| write_file | Write local files | High (requires confirmation) |
| execute_code | Execute code in sandbox | High (requires confirmation, Docker sandbox) |
| get_current_time | Get current time | Low |
| calculator | Math calculation | Low |

## Testing

- Backend: pytest + pytest-asyncio (API + agent runtime + tool execution)
- Frontend: Vitest (components) + Playwright (E2E)
- First write tests, then code