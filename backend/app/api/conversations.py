"""
会话 API — 会话 CRUD + 消息查询

会话是对话的容器，绑定到某个 Agent。
支持按 agent_id 筛选会话列表。
"""

from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationResponse, MessageResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    agent_id: UUID | None = None,
    search: str | None = Query(None, description="按标题模糊搜索（大小写不敏感）"),
    limit: int | None = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取会话列表，可按 Agent 筛选、按标题搜索，按更新时间倒序。支持分页。"""
    query = select(Conversation).order_by(Conversation.updated_at.desc())
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
    if limit is not None:
        query = query.limit(limit).offset(offset)
    else:
        query = query.offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    """创建新会话"""
    conv = Conversation(**data.model_dump())
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除指定会话及其所有消息"""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取指定会话的全部消息，按创建时间正序"""
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取单个会话详情（用于 URL 直接跳转）"""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: UUID,
    format: str = "markdown",
    db: AsyncSession = Depends(get_db),
):
    """导出会话为 markdown 或 json。

    markdown：以标题 + 每条消息（role / 内容）拼成可读文档。
    json：原始结构化数据（含消息列表）。
    """
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    if format == "json":
        payload = {
            "conversation_id": str(conv.id),
            "title": conv.title,
            "agent_id": str(conv.agent_id),
            "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages],
        }
        return _export_response(json.dumps(payload, ensure_ascii=False, indent=2), f"{conv.title}.json", "application/json")

    # markdown
    lines = [f"# {conv.title}", ""]
    role_label = {"user": "🧑 User", "assistant": "🤖 Assistant", "tool": "🔧 Tool"}
    for m in messages:
        lines.append(f"### {role_label.get(m.role, m.role)}")
        lines.append("")
        lines.append(m.content)
        lines.append("")
    return _export_response("\n".join(lines), f"{conv.title}.md", "text/markdown")


def _export_response(content: str, filename: str, media_type: str):
    """构造 Content-Disposition 附件响应。"""
    from fastapi.responses import Response
    safe_name = filename.replace("\n", " ").replace("\r", " ").strip() or "export"
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )