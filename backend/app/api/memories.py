"""
记忆 API — 记忆查询与删除

记忆是 agent_runtime 在每个对话轮次后自动提取的关键信息片段。
支持按 agent_id 和 conversation_id 筛选。
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.memory import Memory
from app.schemas.memory import MemoryResponse

router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    agent_id: UUID | None = Query(None),
    conversation_id: UUID | None = Query(None),
    search: str | None = Query(None, description="按内容关键词模糊搜索（大小写不敏感）"),
    limit: int | None = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取记忆列表，可按 Agent、会话筛选、按内容关键词搜索，按创建时间倒序。支持分页。"""
    stmt = select(Memory).order_by(Memory.created_at.desc())
    if agent_id:
        stmt = stmt.where(Memory.agent_id == agent_id)
    if conversation_id:
        stmt = stmt.where(Memory.conversation_id == conversation_id)
    if search:
        stmt = stmt.where(Memory.content.ilike(f"%{search}%"))
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    else:
        stmt = stmt.offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除单条记忆"""
    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.delete(memory)
    await db.commit()