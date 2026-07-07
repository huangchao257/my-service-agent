"""工具发现 API — 列出所有已注册的内置工具。

GET /api/tools 返回所有工具的 name/description/parameters/risk/category，
供前端在 Agent 配置表单中分组展示可勾选的工具列表。
支持 ?category= 筛选，?risk= 按风险等级筛选。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

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
    """列出所有已注册的内置工具，可按分类与风险等级筛选。

    db 依赖保留是为了未来按 Agent 权限过滤工具；当前返回全部（或筛选后）。"""
    tools = tool_registry.list_all()
    if category:
        tools = [t for t in tools if t.category == category]
    if risk:
        tools = [t for t in tools if t.risk == risk]
    return tools

