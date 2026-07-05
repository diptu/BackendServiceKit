"""Central application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "nutratenant-user-lifecycle-management"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_user_lifecycle",
    )
    database_ssl: bool = Field(default=False)
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # Upstream — the underlying user record this service orchestrates
    # transitions for lives in UserManagement, not here.
    user_management_base_url: str = "http://localhost:8023"
    user_management_timeout: float = 5.0

    # Security
    secret_key: str = "CHANGE_ME"

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8080",  # APIGateway
        ]
    )

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = True
    otlp_endpoint: str = "http://localhost:4317"
    healthcheck_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
