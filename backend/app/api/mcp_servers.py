"""
MCP Server API — CRUD 接口

管理 MCP（Model Context Protocol）服务器配置。
支持两种传输方式：
- stdio：本地进程启动，通过 command + args + env 配置
- http：远程 SSE 端点，通过 url 配置
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mcp_server import MCPServer
from app.schemas.mcp_server import MCPServerCreate, MCPServerUpdate, MCPServerResponse

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp-servers"])


@router.get("", response_model=list[MCPServerResponse])
async def list_mcp_servers(db: AsyncSession = Depends(get_db)):
    """获取所有 MCP 服务器配置列表，按创建时间倒序"""
    result = await db.execute(select(MCPServer).order_by(MCPServer.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=MCPServerResponse, status_code=201)
async def create_mcp_server(data: MCPServerCreate, db: AsyncSession = Depends(get_db)):
    """创建新的 MCP 服务器配置"""
    server = MCPServer(**data.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.put("/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(server_id: UUID, data: MCPServerUpdate, db: AsyncSession = Depends(get_db)):
    """更新 MCP 服务器配置，仅更新传入的字段"""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(server, key, value)
    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=204)
async def delete_mcp_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除指定 MCP 服务器配置"""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    await db.delete(server)
    await db.commit()