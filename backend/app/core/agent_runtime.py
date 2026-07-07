"""
Agent 运行时 — 每次对话轮次的核心编排引擎。

处理流程：
1. 加载 Agent 配置，解析 provider/model（格式："provider名称/model名称"）
2. 加载对话历史（最近 20 条消息）和相关长期记忆
3. 构建完整消息列表：system prompt → 工具列表 → 记忆注入 → 历史消息 → 用户消息
4. 进入工具调用循环（最多 max_tool_rounds 轮）：
   a. 流式调用 LLM，yield delta/tool_call 事件给前端 SSE
   b. 执行工具调用，yield tool_result 事件，将结果追加到消息列表
   c. 工具结果写入 DB，确保刷新页面后上下文不丢失
5. 保存 assistant 消息、记录 LLM 交互日志、提取记忆
6. 首次对话自动通过 LLM 生成会话标题
"""

import json
import time
import asyncio
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.mcp_server import MCPServer
from app.models.provider import LLMProvider
from app.models.skill import Skill
from app.core.llm_gateway import llm_gateway
from app.core.memory_manager import memory_manager
from app.core.mcp_manager import mcp_manager
from app.core.crypto import decrypt
from app.tools import tool_registry

logger = get_logger(__name__)


class AgentRuntime:
    async def _load_skills(self, db: AsyncSession, skill_names: list[str]) -> list[Skill]:
        """按名称加载已激活的 Skill 记录。
        Agent.skills 存储技能名称列表，运行时据此把 prompt_template 注入 system message。
        忽略未知名称，避免单个坏配置阻断整个对话。"""
        if not skill_names:
            return []
        result = await db.execute(
            select(Skill).where(Skill.name.in_(skill_names), Skill.is_active == True)
        )
        # 保持 Agent.skills 中声明的顺序，便于可预测的 prompt 拼装
        by_name = {s.name: s for s in result.scalars().all()}
        return [by_name[n] for n in skill_names if n in by_name]

    async def _load_mcp_servers(self, db: AsyncSession, names: list[str]) -> list[MCPServer]:
        """按名称加载已激活的 MCP 服务器记录。
        Agent.mcp_servers 存储服务器名称列表。忽略未知名称。"""
        if not names:
            return []
        result = await db.execute(
            select(MCPServer).where(MCPServer.name.in_(names), MCPServer.is_active == True)
        )
        by_name = {s.name: s for s in result.scalars().all()}
        return [by_name[n] for n in names if n in by_name]

    @staticmethod
    def _build_messages(agent, skills, memories, history, user_message: str) -> list[dict]:
        """构建发送给 LLM 的完整消息列表。

        顺序：system(含技能模板) → 工具说明 system → 记忆 system → 历史消息 → 用户消息。
        提取为独立方法便于单测消息拼装逻辑，不依赖 DB / LLM。"""
        system_content = agent.system_prompt
        if skills:
            skill_block = "\n\n".join(f"# Skill: {s.name}\n{s.prompt_template}" for s in skills)
            system_content = f"{system_content}\n\n{skill_block}"
        messages: list[dict] = [{"role": "system", "content": system_content}]
        if agent.tools:
            tool_names = ", ".join(agent.tools)
            messages.append({
                "role": "system",
                "content": f"Available tools: {tool_names}. To use a tool, call the function with the required parameters. For web_search, always provide a 'query' parameter with your search query. IMPORTANT: After receiving tool results, ALWAYS provide a text response to the user summarizing what you found. Do not call the same tool with the same parameters repeatedly.",
            })
        if memories:
            memory_text = "Relevant context about the user:\n" + "\n".join(f"- {m}" for m in memories)
            messages.append({"role": "system", "content": memory_text})
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _execute_tool_call(self, agent, tc: dict, user_message: str) -> tuple[str, dict | None]:
        """执行单次工具调用，返回 (tool_result, optional_extra_event)。

        内置工具优先；其次 MCP；未知工具返回错误字符串。
        高风险未授权工具返回跳过提示，并附带 confirmation_required 事件。
        extra_event 为 None 表示无需额外 SSE 事件。"""
        call_id = f"call_{tc.get('_round', 0)}_{tc.get('_index', 0)}"
        tool_def = tool_registry.get(tc["name"])
        if tool_def:
            if tool_def.risk == "high" and tc["name"] not in (agent.high_risk_tools_enabled or []):
                tool_result = f"Tool '{tc['name']}' requires user confirmation. Skipped. Grant access in agent settings to enable it."
                extra = {"event": "confirmation_required", "data": json.dumps({"tool": tc["name"], "arguments": tc["arguments"], "risk": "high"})}
                return tool_result, extra
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                if not args and tc["name"] == "web_search":
                    args = {"query": user_message}
                elif not args:
                    args = {}
                # 执行前按 JSON Schema 校验参数（缺失必填/类型不符），给出清晰错误
                validation_error = tool_registry.validate_args(tc["name"], args)
                if validation_error:
                    return f"Tool error: {validation_error}", None
                result = await asyncio.wait_for(tool_def.function(**args), timeout=settings.tool_timeout)
                return str(result), None
            except asyncio.TimeoutError:
                return f"Tool '{tc['name']}' timed out after {settings.tool_timeout}s", None
            except Exception as e:
                return f"Tool error: {e}", None
        if mcp_manager.has_tool(tc["name"]):
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                out = await asyncio.wait_for(mcp_manager.call_tool(tc["name"], args), timeout=settings.tool_timeout)
                return str(out), None
            except asyncio.TimeoutError:
                return f"MCP tool '{tc['name']}' timed out after {settings.tool_timeout}s", None
            except Exception as e:
                return f"MCP tool error: {e}", None
        return f"Unknown tool: {tc['name']}", None

    async def run(self, db: AsyncSession, agent_id: str, conversation_id: str, user_message: str):
        logger.info("agent_run_start", extra={"agent_id": agent_id, "conversation_id": conversation_id, "msg_len": len(user_message)})
        agent_uuid = UUID(agent_id)
        conv_uuid = UUID(conversation_id)

        # ── 解析 Agent 和 Provider ──
        result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Agent 的 model 字段格式为 "provider名称/model名称"，需要拆解
        model_parts = agent.model.split("/", 1)
        provider = None
        if len(model_parts) == 2:
            provider_result = await db.execute(
                select(LLMProvider).where(LLMProvider.name == model_parts[0], LLMProvider.is_active == True)
            )
            provider = provider_result.scalar_one_or_none()

        # 构建 litellm 兼容的模型字符串："provider类型/model名称"
        actual_model = model_parts[1] if len(model_parts) == 2 else agent.model
        if provider:
            actual_model = f"{provider.provider}/{actual_model}"

        # ── 加载历史消息和长期记忆 ──
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conv_uuid).order_by(Message.created_at.asc()).limit(agent.history_limit)
        )
        history = msg_result.scalars().all()

        # 通过余弦相似度检索最相关的 top_k 条长期记忆（按 Agent 配置覆盖全局默认）
        memories = await memory_manager.retrieve(db, agent_uuid, user_message, top_k=agent.memory_top_k)

        # ── 加载已激活的技能，把 prompt_template 注入 system message ──
        skills = await self._load_skills(db, agent.skills)

        # ── 构建 LLM 消息列表 ──
        messages = self._build_messages(agent, skills, memories, history, user_message)

        # 立即保存用户消息，刷新页面也能看到
        user_msg = Message(conversation_id=conv_uuid, role="user", content=user_message)
        db.add(user_msg)
        await db.commit()

        # ── 解析工具和 API 凭证 ──
        builtin_tools = tool_registry.get_schemas(agent.tools) if agent.tools else []
        # 加载 Agent 配置的 MCP 服务器工具并合并（失败时优雅返回空）
        mcp_servers = await self._load_mcp_servers(db, agent.mcp_servers)
        mcp_schemas = await mcp_manager.get_schemas(mcp_servers) if mcp_servers else []
        tools = (builtin_tools + mcp_schemas) or None
        api_base = provider.api_base if provider else None
        api_key = decrypt(provider.api_key) if provider else None
        # 去掉末尾的 /chat/completions，litellm 内部会自己拼接
        if api_base and api_base.endswith("/chat/completions"):
            api_base = api_base[: -len("/chat/completions")]

        # ── 工具调用循环 ──
        round_count = 0
        full_response = ""
        total_usage = None  # 累计各轮 token 用量
        start_time = time.time()

        try:
            while round_count < settings.max_tool_rounds:
                round_count += 1
                stream = await llm_gateway.chat_completion(
                    model=actual_model, messages=messages, tools=tools,
                    temperature=agent.temperature, max_tokens=agent.max_tokens,
                    api_base=api_base, api_key=api_key,
                    db=db, agent_id=agent_uuid, conversation_id=conv_uuid,
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
                        # 累计 token 用量（最后一轮通常最有意义）
                        if event.get("usage"):
                            total_usage = event["usage"]

                # 没有工具调用说明模型给出了最终文本回复，结束循环
                if not tool_calls_in_round:
                    break

                for i, tc in enumerate(tool_calls_in_round):
                    # 唯一的 call_id 防止跨轮次模型混淆
                    call_id = f"call_{round_count}_{i}"
                    tc["_round"] = round_count
                    tc["_index"] = i
                    tool_result, extra_event = await self._execute_tool_call(agent, tc, user_message)
                    if extra_event:
                        yield extra_event

                    yield {"event": "tool_result", "data": json.dumps({"tool": tc["name"], "output": tool_result})}
                    # 追加到内存消息列表，供下一轮 LLM 调用使用
                    messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}]})
                    # 截断到 2000 字符 — 过长的工具结果会导致模型死循环
                    messages.append({"role": "tool", "content": tool_result[:2000], "tool_call_id": call_id})
                    # 持久化工具结果，刷新页面后上下文不丢失
                    db.add(Message(conversation_id=conv_uuid, role="tool", content=tool_result[:2000]))

            # ── 保存 assistant 消息 ──
            assistant_msg = Message(conversation_id=conv_uuid, role="assistant", content=full_response)
            db.add(assistant_msg)
            await db.commit()

            # ── 记录 LLM 交互日志，用于审计和调试 ──
            duration_ms = int((time.time() - start_time) * 1000)
            await llm_gateway.record_interaction(
                db=db, agent_id=agent_uuid, conversation_id=conv_uuid,
                model=actual_model, messages=messages,
                response_json=json.dumps({"content": full_response}),
                token_usage_json=json.dumps(total_usage) if total_usage else None,
                duration_ms=duration_ms,
            )

            # ── 首次对话自动生成标题 ──
            is_first_message = len(history) == 0
            if is_first_message:
                try:
                    title_response = await llm_gateway.chat_completion(
                        model=actual_model,
                        messages=[{"role": "user", "content": f"Generate a short title (5 words max) for a conversation that starts with this message. Reply in the same language as the message. Return ONLY the title, no quotes, no explanation:\n\n{user_message}"}],
                        stream=False,
                        api_base=api_base, api_key=api_key,
                    )
                    title = title_response.content.strip()[:100] if hasattr(title_response, 'content') else user_message[:50]
                    conv_result = await db.execute(select(Conversation).where(Conversation.id == conv_uuid))
                    conv = conv_result.scalar_one_or_none()
                    if conv:
                        conv.title = title
                        await db.commit()
                        yield {"event": "title_updated", "data": json.dumps({"title": title})}
                except Exception:
                    pass

            # ── 从对话中提取长期记忆 ──
            all_msgs = [{"role": m.role, "content": m.content} for m in history] + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": full_response},
            ]
            await memory_manager.extract_and_store(db, agent_uuid, all_msgs, conv_uuid, model=actual_model, api_base=api_base, api_key=api_key)

            done_payload = {"conversation_id": str(conversation_id)}
            if total_usage:
                done_payload["token_usage"] = total_usage
            logger.info("agent_run_done", extra={"conversation_id": str(conversation_id), "rounds": round_count, "tokens": total_usage})
            yield {"event": "done", "data": json.dumps(done_payload)}
        finally:
            # 无论正常结束还是异常，都释放 MCP 客户端连接
            await mcp_manager.close()


agent_runtime = AgentRuntime()