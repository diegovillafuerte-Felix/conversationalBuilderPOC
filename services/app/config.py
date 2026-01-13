"""Configuration for services gateway."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service gateway settings."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    # API
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    class Config:
        env_prefix = "SERVICES_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
