"""
LLM Provider API — CRUD 接口 + 可用模型列表

管理 LLM 提供商配置（API 地址、密钥、可用模型列表）。
列表接口会对 API Key 做脱敏处理。
"""

from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException, Query
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
async def list_providers(
    limit: int | None = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取所有 Provider 列表，API Key 中间部分用 **** 脱敏。支持分页。"""
    query = select(LLMProvider).order_by(LLMProvider.created_at.desc())
    if limit is not None:
        query = query.limit(limit).offset(offset)
    else:
        query = query.offset(offset)
    result = await db.execute(query)
    providers = result.scalars().all()
    # 在响应层脱敏，不修改 ORM 实例
    return [ProviderResponse.masked(p) for p in providers]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取单个 Provider 详情，API Key 脱敏"""
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse.masked(provider)


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


@router.post("/{provider_id}/test")
async def test_provider_connection(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """测试 Provider 连通性：用配置的凭证发一次极小请求（max_tokens=1）。

    返回 {ok: bool, detail: str}。不抛异常——把错误信息原样返回给前端展示。"""
    import litellm
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # 选第一个模型做探测；无模型则用 provider 类型本身
    probe_model = provider.models[0] if provider.models else "gpt-3.5-turbo"
    actual_model = f"{provider.provider}/{probe_model}"
    api_base = provider.api_base
    if api_base and api_base.endswith("/chat/completions"):
        api_base = api_base[: -len("/chat/completions")]
    try:
        await litellm.acompletion(
            model=actual_model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            api_base=api_base,
            api_key=provider.api_key,
            timeout=15,
        )
        return {"ok": True, "detail": "connection successful"}
    except Exception as e:
        return {"ok": False, "detail": f"{type(e).__name__}: {e}"}


@router.post("/{provider_id}/refresh-models", response_model=ProviderResponse)
async def refresh_provider_models(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """从 Provider API 拉取可用模型列表并更新配置。

    对 OpenAI 兼容的 api_base，直接 GET {api_base}/models 解析 data[].id。
    失败时保持现有列表不变（不抛异常），前端可据此提示。"""
    import httpx
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    api_base = provider.api_base
    if api_base and api_base.endswith("/chat/completions"):
        api_base = api_base[: -len("/chat/completions")]
    if not api_base:
        return provider
    models_url = api_base.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.get(models_url, headers={"Authorization": f"Bearer {provider.api_key}"})
        if resp.status_code == 200:
            data = resp.json().get("data") or []
            ids = [m.get("id") for m in data if m.get("id")]
            if ids:
                provider.models = sorted({i for i in ids if i})
                await db.commit()
                await db.refresh(provider)
                await cache.delete(_MODELS_CACHE_KEY)
    except Exception:
        # 拉取失败保持现状
        pass
    return provider