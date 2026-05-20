"""
LLM 网关 — 封装 litellm 的薄层，统一处理所有模型交互。

支持两种模式：
- 流式：yield {"type": "delta"|"tool_call"|"done"} 字典，供 SSE 推送
- 非流式：直接返回完整的响应消息

同时提供文本嵌入向量生成和交互日志记录功能。
仅在传入 db/agent_id 参数时才记录交互 —
流式调用需单独调用 record_interaction()，因为完整响应要等流结束后才能获得。
"""

import json
import time
from typing import AsyncIterator
from uuid import UUID
import litellm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_interaction import LLMInteraction


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
        # 可选 — 传入后非流式调用自动记录交互日志
        db: AsyncSession | None = None,
        agent_id: UUID | None = None,
        conversation_id: UUID | None = None,
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
            start_time = time.time()
            response = await litellm.acompletion(**kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            # 非流式调用自动记录（用于标题生成、记忆提取等场景）
            if db and agent_id:
                db.add(LLMInteraction(
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    model=model,
                    messages_json=json.dumps(messages),
                    response_json=response.model_dump_json() if hasattr(response, 'model_dump_json') else json.dumps(str(response)),
                    duration_ms=duration_ms,
                ))
                await db.commit()
            return response.choices[0].message

    async def _stream_response(self, **kwargs) -> AsyncIterator[dict]:
        """流式 SSE 事件生成：delta（文本片段）→ tool_call → done。
        tool_call 的 arguments 按 index 缓冲，因为 litellm 会分多个 chunk 下发。"""
        response = await litellm.acompletion(**kwargs)
        tool_call_buffers: dict[int, dict] = {}
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "delta", "content": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {"name": "", "arguments": ""}
                    if tc.function and tc.function.name:
                        tool_call_buffers[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_call_buffers[idx]["arguments"] += tc.function.arguments
        for buf in tool_call_buffers.values():
            if buf["name"]:
                yield {"type": "tool_call", "name": buf["name"], "arguments": buf["arguments"]}
        yield {"type": "done"}

    async def record_interaction(
        self, db: AsyncSession, agent_id: UUID, conversation_id: UUID | None,
        model: str, messages: list[dict], response_json: str,
        token_usage_json: str | None = None, duration_ms: int | None = None,
    ):
        """显式记录流式交互 — 在流结束后调用，此时已获知完整响应。"""
        db.add(LLMInteraction(
            agent_id=agent_id,
            conversation_id=conversation_id,
            model=model,
            messages_json=json.dumps(messages),
            response_json=response_json,
            token_usage_json=token_usage_json,
            duration_ms=duration_ms,
        ))
        await db.commit()

    async def get_embedding(self, text: str, api_base: str | None = None, api_key: str | None = None) -> list[float]:
        """生成文本嵌入向量（默认 1536 维）。
        失败时返回零向量而非抛异常，让调用方在嵌入服务不可用时优雅降级。"""
        kwargs = {
            "model": "text-embedding-3-small",
            "input": [text],
        }
        if api_base:
            kwargs["api_base"] = api_base
        if api_key:
            kwargs["api_key"] = api_key
        try:
            response = await litellm.aembedding(**kwargs)
            return response.data[0]["embedding"]
        except Exception:
            return [0.0] * 1536


llm_gateway = LLMGateway()