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
    async def run(self, db: AsyncSession, agent_id: str, conversation_id: str, user_message: str):
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        model_parts = agent.model.split("/", 1)
        provider = None
        if len(model_parts) == 2:
            provider_result = await db.execute(
                select(LLMProvider).where(LLMProvider.name == model_parts[0], LLMProvider.is_active == True)
            )
            provider = provider_result.scalar_one_or_none()

        actual_model = model_parts[1] if len(model_parts) == 2 else agent.model

        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).limit(20)
        )
        history = msg_result.scalars().all()

        memories = await memory_manager.retrieve(db, agent_id, user_message)

        messages = [{"role": "system", "content": agent.system_prompt}]
        if memories:
            memory_text = "Relevant context about the user:\n" + "\n".join(f"- {m}" for m in memories)
            messages.append({"role": "system", "content": memory_text})
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        user_msg = Message(conversation_id=conversation_id, role="user", content=user_message)
        db.add(user_msg)
        await db.commit()

        tools = tool_registry.get_schemas(agent.tools) if agent.tools else None
        api_base = provider.api_base if provider else None
        api_key = provider.api_key if provider else None

        round_count = 0
        full_response = ""

        while round_count < settings.max_tool_rounds:
            round_count += 1
            stream = await llm_gateway.chat_completion(
                model=actual_model, messages=messages, tools=tools,
                temperature=agent.temperature, max_tokens=agent.max_tokens,
                api_base=api_base, api_key=api_key,
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
                break

            for tc in tool_calls_in_round:
                tool_def = tool_registry.get(tc["name"])
                if tool_def:
                    if tool_def.risk == "high":
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

        assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=full_response)
        db.add(assistant_msg)
        await db.commit()

        all_msgs = [{"role": m.role, "content": m.content} for m in history] + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": full_response},
        ]
        await memory_manager.extract_and_store(db, agent_id, all_msgs)

        yield {"event": "done", "data": json.dumps({"conversation_id": str(conversation_id)})}


agent_runtime = AgentRuntime()