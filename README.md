# my-service-agent

个人多 Agent 聊天平台。后端 FastAPI + litellm，前端 Next.js 16 + shadcn/ui，PostgreSQL + Redis 存储。

## 功能特性

- **多 Agent 管理**：每个 Agent 绑定一个 LLM Provider、系统提示、工具集、技能、MCP 服务器
- **SSE 流式对话**：实时输出文本增量、工具调用卡片，支持中途取消
- **工具调用**：内置 6 个工具（时间/计算器/网页搜索/文件读写/代码执行），支持多轮调用与超时保护
- **MCP 协议**：接入外部 MCP 服务器工具（stdio/http，`mcp` 库可选，优雅降级）
- **长期记忆**：基于嵌入的余弦相似度语义检索，自动从对话中提取并去重
- **技能模板**：可复用 prompt 模板，注入 system message
- **高风险工具确认**：白名单授权机制，未授权工具触发前端确认提示
- **LLM 交互审计**：完整上下文快照、token 用量、耗时记录与查看
- **健壮性**：LLM 瞬态错误重试、客户端断连检测、结构化日志、进程内限流、API Key 静态加密
- **会话管理**：标题搜索、消息重生、Markdown/JSON 导出、Agent 复制
- **Provider 运维**：连通性测试、模型列表自动拉取

## 快速开始

### Docker（推荐）

```bash
# 生成 API Key 加密密钥（可选但建议）
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 把上面的输出填入 docker-compose.yml 的 ENCRYPTION_KEY

docker compose up -d          # 启动 db + redis + backend + frontend
# 后端 http://localhost:8000  前端 http://localhost:3000
```

### 本地开发

```bash
# 基础设施
docker compose up -d db redis

# 后端
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev    # http://localhost:3000
```

## 测试

```bash
cd backend
.venv/bin/pip install pytest pytest-asyncio   # 测试依赖
.venv/bin/pytest -v
```

## 配置

后端通过环境变量 / `backend/.env` 配置（见 `app/config.py`）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `DATABASE_URL` | sqlite | PostgreSQL: `postgresql+asyncpg://...` |
| `REDIS_URL` | `redis://localhost:6379/0` | 缓存；不可用时降级到内存 |
| `LLM_TIMEOUT` | 60 | LLM 调用超时（秒） |
| `LLM_MAX_RETRIES` | 3 | 瞬态错误重试次数 |
| `TOOL_TIMEOUT` | 30 | 单个工具执行超时（秒） |
| `MAX_TOOL_ROUNDS` | 10 | 工具调用循环上限 |
| `MEMORY_TOP_K` | 5 | 记忆检索默认条数 |
| `ENCRYPTION_KEY` | 空 | Fernet 密钥；空则 api_key 明文存储 |

## 架构

详见 [CLAUDE.md](./CLAUDE.md)。
