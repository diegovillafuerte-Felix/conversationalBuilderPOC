"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # App
    app_name: str = "Felix Orchestrator"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # OpenAI
    openai_api_key: str

    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite+aiosqlite:///./felix_orchestrator.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM defaults
    default_model: str = "gpt-5.2"
    default_temperature: float = 0.7
    default_max_tokens: int = 1024

    # Token budgets for context assembly
    token_budget_system_prompt: int = 1000
    token_budget_user_profile: int = 500
    token_budget_product_context: int = 500
    token_budget_conversation_recent: int = 2000
    token_budget_conversation_compacted: int = 500
    token_budget_current_state: int = 300
    token_budget_tool_definitions: int = 1000
    token_budget_buffer: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
