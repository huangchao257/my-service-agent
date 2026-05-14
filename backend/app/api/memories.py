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
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Memory).order_by(Memory.created_at.desc())
    if agent_id:
        stmt = stmt.where(Memory.agent_id == agent_id)
    if conversation_id:
        stmt = stmt.where(Memory.conversation_id == conversation_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.delete(memory)
    await db.commit()