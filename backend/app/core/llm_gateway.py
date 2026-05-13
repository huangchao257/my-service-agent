import json
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
        try:
            response = await litellm.aembedding(**kwargs)
            return response.data[0]["embedding"]
        except Exception:
            return [0.0] * 1536


llm_gateway = LLMGateway()