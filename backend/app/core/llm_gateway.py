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