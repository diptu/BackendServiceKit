"""Central application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "nutratenant-api-gateway"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Redis — DB 3 for response cache
    redis_url: str = "redis://localhost:6379/3"
    redis_tenant_cache_ttl: int = 300   # 5 min: tenant detail responses
    redis_lifecycle_cache_ttl: int = 60  # 1 min: lifecycle history responses

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "api-gateway.events"
    rabbitmq_tenant_events_exchange: str = "tenant.events"
    rabbitmq_tenant_events_queue: str = "api-gateway.tenant-events"

    # Celery (uses RabbitMQ as broker)
    celery_broker_url: str = "amqp://guest:guest@localhost:5672/"
    celery_result_backend: str = "redis://localhost:6379/5"

    # Upstream services
    tenant_management_base_url: str = "http://localhost:8001"
    tenant_lifecycle_base_url: str = "http://localhost:8002"
    tenant_provisioning_base_url: str = "http://localhost:8003"
    redis_provisioning_cache_ttl: int = 30
    upstream_timeout: float = 30.0

    # Security
    secret_key: str = "CHANGE_ME"

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8001",
            "http://localhost:8002",
        ]
    )

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = True
    otlp_endpoint: str = "http://localhost:4317"

    # Health check
    healthcheck_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
