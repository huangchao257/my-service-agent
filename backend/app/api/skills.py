"""
技能 API — CRUD 接口

技能是预编写的 prompt 模板，可分配给 Agent 注入到 system message 中。
category 用于前端分类展示（如 "coding"、"writing"、"general"）。
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
async def list_skills(db: AsyncSession = Depends(get_db)):
    """获取所有技能列表，按创建时间倒序"""
    result = await db.execute(select(Skill).order_by(Skill.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=SkillResponse, status_code=201)
async def create_skill(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    """创建新技能"""
    skill = Skill(**data.model_dump())
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: UUID, data: SkillUpdate, db: AsyncSession = Depends(get_db)):
    """更新技能，仅更新传入的字段"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(skill, key, value)
    await db.commit()
    await db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除指定技能"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await db.delete(skill)
    await db.commit()