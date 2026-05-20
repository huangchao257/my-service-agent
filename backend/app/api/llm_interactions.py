"""
LLM 交互记录 API — 仅查看

记录每次调用 LLM 的完整上下文快照（system prompt + 记忆注入 + 历史消息 + 用户消息）、
模型响应、token 用量和耗时。支持分页和筛选。
"""

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
    """获取 LLM 交互记录分页列表，可按 Agent 和会话筛选"""
    stmt = select(LLMInteraction).order_by(LLMInteraction.created_at.desc())
    if agent_id:
        stmt = stmt.where(LLMInteraction.agent_id == agent_id)
    if conversation_id:
        stmt = stmt.where(LLMInteraction.conversation_id == conversation_id)

    # 统计总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return LLMInteractionListResponse(items=items, total=total)


@router.get("/{interaction_id}", response_model=LLMInteractionResponse)
async def get_llm_interaction(interaction_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取单条 LLM 交互记录详情（含完整 messages_json）"""
    result = await db.execute(select(LLMInteraction).where(LLMInteraction.id == interaction_id))
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction