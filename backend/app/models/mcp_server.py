"""MCP（Model Context Protocol）服务器配置。

支持两种传输方式：
- stdio：在本地启动进程，通过 command + args + env 配置
- http：连接远程 SSE 端点，通过 url 配置"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    transport: Mapped[str] = mapped_column(String(20), default="stdio")  # "stdio" 或 "http"
    command: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # stdio 传输时使用
    args_json: Mapped[str] = mapped_column(Text, default="[]")  # CLI 参数 JSON 数组
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)  # HTTP 传输时使用
    env_json: Mapped[str] = mapped_column(Text, default="{}")  # 环境变量 JSON 对象
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())