"""Central application configuration.

All settings are loaded from environment variables and optionally from .env.

This module acts as the single source of truth for configuration across
the service.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------------------------------------------------
    # Application
    # ---------------------------------------------------------------------
    app_name: str = "nutratenant-identity-service"
    app_version: str = "0.1.0"

    environment: Literal[
        "development",
        "testing",
        "staging",
        "production",
    ] = "development"

    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # ---------------------------------------------------------------------
    # Database
    # ---------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_identity",
        description="Primary PostgreSQL connection string.",
    )

    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # ---------------------------------------------------------------------
    # Redis
    # ---------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # ---------------------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------------------
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "identity.events"

    # ---------------------------------------------------------------------
    # Security
    # ---------------------------------------------------------------------
    secret_key: str = "CHANGE_ME"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # ---------------------------------------------------------------------
    # Rate Limiting
    # ---------------------------------------------------------------------
    rate_limit_enabled: bool = True
    default_rate_limit: str = "100/minute"

    # ---------------------------------------------------------------------
    # CORS
    # ---------------------------------------------------------------------
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8000",
        ]
    )

    # ---------------------------------------------------------------------
    # Observability
    # ---------------------------------------------------------------------
    enable_metrics: bool = True
    enable_tracing: bool = True

    otlp_endpoint: str = "http://localhost:4317"

    # ---------------------------------------------------------------------
    # Health Checks
    # ---------------------------------------------------------------------
    healthcheck_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Settings are loaded only once during process lifetime.
    """
    return Settings()


settings = get_settings()