"""工具发现与执行 API。

GET  /api/tools                  — 列出全部已注册工具（支持 category/risk 筛选）
GET  /api/tools/metrics          — 各工具调用指标
POST /api/tools/{name}/run       — 直接运行某个工具（工具广场用）

运行端点复用 runtime 的校验/超时/指标逻辑，但不经过 LLM——用户在工具广场
页面上手动填参数后直接调用，便于调试和日常开发使用。
"""

import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.tools import tool_registry
from app.schemas.tool import ToolResponse

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    category: str | None = Query(None, description="按分类筛选：system/web/file/code/dev"),
    risk: str | None = Query(None, description="按风险等级筛选：low/medium/high"),
    db: AsyncSession = Depends(get_db),
):
    """列出所有已注册的内置工具，可按分类与风险等级筛选。"""
    tools = tool_registry.list_all()
    if category:
        tools = [t for t in tools if t.category == category]
    if risk:
        tools = [t for t in tools if t.risk == risk]
    return tools


@router.get("/metrics")
async def tool_metrics(db: AsyncSession = Depends(get_db)):
    """返回各工具的调用次数、错误数、平均耗时，供运维观测。"""
    return tool_registry.get_metrics()


class ToolRunRequest(BaseModel):
    """工具运行请求。args 为参数字典；高风险工具需显式 confirm。"""
    args: dict = {}
    confirm_high_risk: bool = False


@router.post("/{name}/run")
async def run_tool(name: str, data: ToolRunRequest, db: AsyncSession = Depends(get_db)):
    """直接运行某个工具，返回执行结果。

    - 高风险工具（write_file/execute_code）需 confirm_high_risk=true 才执行，否则 400。
    - 执行前走 validate_args 校验必填与类型。
    - 超时保护（settings.tool_timeout）+ 调用指标记录。
    - 返回 {success, result, duration_ms}；失败时 success=false，result 为错误信息。
    """
    tool_def = tool_registry.get(name)
    if not tool_def:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")

    if tool_def.risk == "high" and not data.confirm_high_risk:
        raise HTTPException(
            status_code=400,
            detail=f"Tool '{name}' is high-risk. Set confirm_high_risk=true to acknowledge and run.",
        )

    args = dict(data.args or {})
    # 参数校验（缺失必填/类型不符）
    validation_error = tool_registry.validate_args(name, args)
    if validation_error:
        return {"success": False, "result": validation_error, "duration_ms": 0}

    start = time.time()
    try:
        raw = await asyncio.wait_for(tool_def.function(**args), timeout=settings.tool_timeout)
        duration_ms = round((time.time() - start) * 1000, 2)
        tool_registry.record_call(name, duration_ms, success=True)
        return {"success": True, "result": str(raw), "duration_ms": duration_ms}
    except asyncio.TimeoutError:
        duration_ms = round(settings.tool_timeout * 1000, 2)
        tool_registry.record_call(name, duration_ms, success=False)
        return {"success": False, "result": f"timed out after {settings.tool_timeout}s", "duration_ms": duration_ms}
    except Exception as e:
        duration_ms = round((time.time() - start) * 1000, 2)
        tool_registry.record_call(name, duration_ms, success=False)
        return {"success": False, "result": f"Error: {e}", "duration_ms": duration_ms}
