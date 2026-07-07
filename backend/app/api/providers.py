"""
LLM Provider API — CRUD 接口 + 可用模型列表

管理 LLM 提供商配置（API 地址、密钥、可用模型列表）。
列表接口会对 API Key 做脱敏处理。
"""

from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.provider import LLMProvider
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse
from app.core.cache import cache

router = APIRouter(prefix="/api/providers", tags=["providers"])

# 模型聚合列表的缓存键与 TTL
_MODELS_CACHE_KEY = "providers:models:active"
_MODELS_CACHE_TTL = 60  # 秒


@router.get("/models")
async def list_available_models(db: AsyncSession = Depends(get_db)):
    """汇总所有已激活 Provider 的模型列表，供前端下拉选择。

    结果缓存 60 秒（Redis 不可用时降级到内存），任何 Provider 写操作都会失效缓存。"""
    cached = await cache.get(_MODELS_CACHE_KEY)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass  # 缓存损坏则回源

    result = await db.execute(
        select(LLMProvider).where(LLMProvider.is_active == True)
    )
    providers = result.scalars().all()
    models: list[dict] = []
    for p in providers:
        for m in p.models:
            models.append({
                "value": f"{p.name}/{m}",
                "label": f"{p.provider}/{m}",
                "provider_name": p.name,
                "provider_id": str(p.id),
            })
    await cache.set(_MODELS_CACHE_KEY, json.dumps(models), ttl=_MODELS_CACHE_TTL)
    return models


@router.get("", response_model=list[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    """获取所有 Provider 列表，API Key 中间部分用 **** 脱敏"""
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.created_at.desc()))
    providers = result.scalars().all()
    for p in providers:
        if p.api_key and len(p.api_key) > 8:
            p.api_key = p.api_key[:4] + "****" + p.api_key[-4:]
    return providers


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取单个 Provider 详情，API Key 脱敏"""
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider.api_key and len(provider.api_key) > 8:
        provider.api_key = provider.api_key[:4] + "****" + provider.api_key[-4:]
    return provider


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    """创建新的 LLM Provider 配置"""
    provider = LLMProvider(**data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    await cache.delete(_MODELS_CACHE_KEY)
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: UUID, data: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    """更新 Provider 配置，仅更新传入的字段"""
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    await cache.delete(_MODELS_CACHE_KEY)
    return provider


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除指定 Provider"""
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
    await cache.delete(_MODELS_CACHE_KEY)