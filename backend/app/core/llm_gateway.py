"""
LLM 网关 — 封装 litellm 的薄层，统一处理所有模型交互。

支持两种模式：
- 流式：yield {"type": "delta"|"tool_call"|"done"} 字典，供 SSE 推送
- 非流式：直接返回完整的响应消息

瞬态错误（超时 / 限流 / 5xx）会按指数退避重试，最多 llm_max_retries 次。
仅非流式调用在传入 db/agent_id 时自动记录交互日志 —
流式调用需单独调用 record_interaction()，因为完整响应要等流结束后才能获得。
"""

import json
import time
import asyncio
from typing import AsyncIterator
from uuid import UUID
import litellm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.models.llm_interaction import LLMInteraction

logger = get_logger(__name__)


def _is_transient(exc: Exception) -> bool:
    """判断异常是否为可重试的瞬态错误（超时 / 限流 / 服务端 5xx / 连接错误）。

    litellm 会把各提供商的错误归一为 openai 风格异常，这里按类名与状态码双重判断，
    尽量宽松地捕获可重试场景，避免漏掉自定义提供商的异常类型。"""
    name = type(exc).__name__
    transient_names = {
        "Timeout", "APITimeoutError",
        "RateLimitError", "RateLimitExceededError",
        "APIConnectionError", "ConnectionError", "ConnectionResetError",
        "ServiceUnavailableError", "InternalServerError", "APIStatusError",
    }
    if name in transient_names:
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "statusCode", None)
    if isinstance(status, int) and (status == 429 or status >= 500):
        return True
    return False


class LLMGateway:
    async def _call_with_retry(self, **kwargs):
        """带指数退避的重试封装，仅重试瞬态错误。
        流式调用重试的是“建立流”这一步；一旦开始迭代 chunk 则不再重试。"""
        last_exc: Exception | None = None
        for attempt in range(settings.llm_max_retries + 1):
            try:
                return await litellm.acompletion(**kwargs)
            except Exception as exc:
                last_exc = exc
                # 非瞬态错误或已用尽重试次数，直接抛出
                if not _is_transient(exc) or attempt == settings.llm_max_retries:
                    raise
                delay = settings.llm_retry_base_delay * (2 ** attempt)
                logger.warning("llm_retry", extra={"attempt": attempt + 1, "delay": delay, "error": type(exc).__name__})
                await asyncio.sleep(delay)
        # 理论不可达：循环要么 return 要么 raise
        raise last_exc  # pragma: no cover

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
            response = await self._call_with_retry(**kwargs)
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
        tool_call 的 arguments 按 index 缓冲，因为 litellm 会分多个 chunk 下发。
        开启 stream_options.include_usage，使最终 chunk 携带 token 用量，
        在 done 事件中一并返回，供上层记录到 llm_interactions。"""
        # 请求服务端在末尾 chunk 附带 usage 统计
        kwargs.setdefault("stream_options", {"include_usage": True})
        response = await self._call_with_retry(**kwargs)
        tool_call_buffers: dict[int, dict] = {}
        usage: dict | None = None
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield {"type": "delta", "content": delta.content}
            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {"name": "", "arguments": ""}
                    if tc.function and tc.function.name:
                        tool_call_buffers[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_call_buffers[idx]["arguments"] += tc.function.arguments
            # usage 通常出现在 choices 为空的末尾 chunk
            if getattr(chunk, "usage", None):
                try:
                    usage = chunk.usage.model_dump() if hasattr(chunk.usage, "model_dump") else dict(chunk.usage)
                except Exception:
                    usage = None
        for buf in tool_call_buffers.values():
            if buf["name"]:
                yield {"type": "tool_call", "name": buf["name"], "arguments": buf["arguments"]}
        yield {"type": "done", "usage": usage}

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