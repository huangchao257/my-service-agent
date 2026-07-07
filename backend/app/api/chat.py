"""
聊天 API — SSE 流式对话接口

POST /api/chat/{conversation_id} 发起一轮对话。
后端通过 SSE 实时推送：delta（文本增量）→ tool_call → tool_result → done。

客户端断连检测：流式过程中若发现客户端已断开（AbortController / 关闭页面），
立即停止迭代，agent_runtime 的 finally 会释放 MCP 等资源，避免空跑。
"""

from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ChatRequest
from app.core.agent_runtime import agent_runtime

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _stream_runtime(db, agent_id, conversation_id, user_message, request):
    """通用 SSE 包装：迭代 agent_runtime.run，处理断连与异常。"""
    async def event_stream():
        try:
            async for event in agent_runtime.run(
                db=db, agent_id=agent_id, conversation_id=conversation_id, user_message=user_message,
            ):
                if await request.is_disconnected():
                    break
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{conversation_id}")
async def chat(conversation_id: UUID, data: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """SSE 流式对话端点。

    事件类型：
    - delta: LLM 文本增量输出
    - tool_call: Agent 调用工具
    - tool_result: 工具执行结果
    - delta: 工具结果注入后 LLM 继续输出（可多轮）
    - confirmation_required: 高风险工具未授权，需用户确认
    - title_updated: 首次对话完成后自动生成标题
    - done: 对话完成
    - error: 异常信息
    """
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await _stream_runtime(db, str(conv.agent_id), str(conversation_id), data.message, request)


@router.post("/{conversation_id}/regenerate")
async def regenerate(conversation_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    """重生成最后一轮回复：删除末尾的 user/tool/assistant 消息，用原 user 文本重跑。

    定位最后一条 user 消息，删除它及其之后的所有消息，再用其内容重新发起对话。
    若没有可重生的 user 消息则返回 400。"""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    # 找到最后一条 user 消息
    last_user_idx = -1
    for i, m in enumerate(messages):
        if m.role == "user":
            last_user_idx = i
    if last_user_idx < 0:
        raise HTTPException(status_code=400, detail="No user message to regenerate from")

    user_text = messages[last_user_idx].content
    ids_to_delete = [m.id for m in messages[last_user_idx:]]
    await db.execute(delete(Message).where(Message.id.in_(ids_to_delete)))
    await db.commit()

    return await _stream_runtime(db, str(conv.agent_id), str(conversation_id), user_text, request)