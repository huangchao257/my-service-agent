"""
Agent API — CRUD 接口

提供 Agent 的创建、查询、更新、删除功能。
Agent 是平台的核心实体，每个 Agent 绑定一个 LLM 模型和一组工具。
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    limit: int | None = Query(None, ge=1, description="限制返回数量，不传则返回全部"),
    offset: int = Query(0, ge=0, description="偏移量，用于分页"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有 Agent 列表，按创建时间倒序。支持 limit/offset 分页。"""
    query = select(Agent).order_by(Agent.created_at.desc())
    if limit is not None:
        query = query.limit(limit).offset(offset)
    else:
        query = query.offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取单个 Agent 详情"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """创建新的 Agent"""
    agent = Agent(**data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: UUID, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    """更新 Agent 配置，仅更新传入的字段"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除指定 Agent"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/duplicate", response_model=AgentResponse, status_code=201)
async def duplicate_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """复制 Agent 配置，生成一个带 "(copy)" 后缀的新 Agent。

    复制所有配置字段（system_prompt / model / tools / skills / 高风险工具白名单 / 温度等），
    但不复制身份字段（id / 时间戳）。方便基于现有 Agent 快速派生。"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    clone = Agent(
        name=f"{agent.name} (copy)",
        avatar=agent.avatar,
        system_prompt=agent.system_prompt,
        model=agent.model,
        tools=list(agent.tools or []),
        mcp_servers=list(agent.mcp_servers or []),
        skills=list(agent.skills or []),
        high_risk_tools_enabled=list(agent.high_risk_tools_enabled or []),
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return clone