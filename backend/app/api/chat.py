"""
聊天 API — SSE 流式对话接口

POST /api/chat/{conversation_id} 发起一轮对话。
后端通过 SSE 实时推送：delta（文本增量）→ tool_call → tool_result → done。
"""

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
    """SSE 流式对话端点。

    事件类型：
    - delta: LLM 文本增量输出
    - tool_call: Agent 调用工具
    - tool_result: 工具执行结果
    - delta: 工具结果注入后 LLM 继续输出（可多轮）
    - title_updated: 首次对话完成后自动生成标题
    - done: 对话完成
    - error: 异常信息
    """
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_stream():
        try:
            async for event in agent_runtime.run(
                db=db, agent_id=str(conv.agent_id), conversation_id=str(conversation_id), user_message=data.message,
            ):
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")