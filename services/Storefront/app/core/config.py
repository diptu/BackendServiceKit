"""Central application configuration for the Storefront service."""

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
    app_name: str = "nutratenant-storefront"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database — the "control plane" / default database. In siloed mode this is
    # only used by Alembic and the readiness probe; live requests route to the
    # per-tenant database resolved from the X-Tenant-ID header.
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_storefront",
    )
    database_ssl: bool = Field(default=False)
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # ---------------------------------------------------------------------
    # Physical silo (database-per-tenant). ON by default for this service —
    # each shop's catalog/cart/orders live in that tenant's own database,
    # resolved per request from X-Tenant-ID. See app/infrastructure/database/
    # tenant_routing.py and scripts/tenant_migrations.py.
    # ---------------------------------------------------------------------
    siloed_multitenancy_enabled: bool = True
    tenant_database_url_template: str | None = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/storefront_{tenant_id}"
    )
    tenant_database_overrides: dict[str, str] = Field(default_factory=dict)
    tenant_max_engines: int | None = None
    tenant_resolver: Literal["template", "control_plane"] = "template"
    control_plane_base_url: str | None = None
    control_plane_timeout: float = 5.0

    # Messaging — storefront domain events (order.placed, order.fulfilled ...).
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "storefront.events"

    # Security
    secret_key: str = "CHANGE_ME"

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
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
