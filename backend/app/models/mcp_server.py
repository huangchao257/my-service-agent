import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    transport: Mapped[str] = mapped_column(String(20), default="stdio")
    command: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    args_json: Mapped[str] = mapped_column(Text, default="[]")
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    env_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())