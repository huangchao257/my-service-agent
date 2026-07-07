"""
应用配置 — 通过环境变量或 .env 文件加载

所有配置项都有合理的默认值，生产环境建议通过环境变量覆盖。
配置优先级：环境变量 > .env 文件 > 默认值
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 数据库连接 — 支持 SQLite 和 PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./agent_platform.db"

    # Redis 连接 — 用于缓存
    redis_url: str = "redis://localhost:6379/0"

    # JWT / Session 密钥
    secret_key: str = "dev-secret-key-change-in-production"

    # LLM 调用超时（秒）
    llm_timeout: int = 60

    # LLM 瞬态错误最大重试次数（超时 / 限流 / 5xx）
    llm_max_retries: int = 3

    # 重试退避基础延迟（秒），实际延迟 = base * 2**attempt
    llm_retry_base_delay: float = 1.0

    # 单个工具执行超时（秒）
    tool_timeout: int = 30

    # 工具调用最大轮次 — 防止死循环
    max_tool_rounds: int = 10

    # 会话超时（秒）
    conversation_timeout: int = 300

    # 记忆检索返回条数
    memory_top_k: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


# 全局配置单例
settings = Settings()