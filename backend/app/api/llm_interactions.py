from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.llm_interaction import LLMInteraction
from app.schemas.llm_interaction import LLMInteractionResponse, LLMInteractionListResponse

router = APIRouter(prefix="/api/llm-interactions", tags=["llm-interactions"])


@router.get("", response_model=LLMInteractionListResponse)
async def list_llm_interactions(
    agent_id: UUID | None = Query(None),
    conversation_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LLMInteraction).order_by(LLMInteraction.created_at.desc())
    if agent_id:
        stmt = stmt.where(LLMInteraction.agent_id == agent_id)
    if conversation_id:
        stmt = stmt.where(LLMInteraction.conversation_id == conversation_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return LLMInteractionListResponse(items=items, total=total)


@router.get("/{interaction_id}", response_model=LLMInteractionResponse)
async def get_llm_interaction(interaction_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMInteraction).where(LLMInteraction.id == interaction_id))
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction