from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agent:agent123@localhost:5432/agent_platform"
    secret_key: str = "dev-secret-key-change-in-production"
    llm_timeout: int = 60
    tool_timeout: int = 30
    max_tool_rounds: int = 10
    conversation_timeout: int = 300
    memory_top_k: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()