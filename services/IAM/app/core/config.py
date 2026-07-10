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
        description="Primary PostgreSQL connection string (shared-schema mode).",
    )

    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # ---------------------------------------------------------------------
    # Siloed multi-tenancy (database-per-tenant) — see TODO.md
    #
    # Opt-in. When disabled (default) IAM uses the single shared-schema
    # `database_url` above. When enabled, every request routes to its own
    # tenant database resolved from `tenant_database_url_template` (with a
    # `{tenant}` placeholder substituted by the tenant's hex id), and a
    # request carrying no tenant fails closed — there is no shared fallback.
    # `tenant_database_overrides` maps a tenant UUID (string) to an explicit
    # connection string for tenants whose database lives elsewhere. This is a
    # stand-in for the Tenent-owned Control Plane registry.
    # ---------------------------------------------------------------------
    siloed_multitenancy_enabled: bool = False
    tenant_database_url_template: str | None = None
    tenant_database_overrides: dict[str, str] = Field(default_factory=dict)
    tenant_max_engines: int | None = None  # bound hot per-tenant pools; None=∞

    # How a tenant is resolved to a connection string:
    #   "template"      — derive from tenant_database_url_template (dev/simple)
    #   "control_plane" — fetch each tenant's DSN from the Tenent Control Plane
    #                     (production; the tenant→database map + credentials live
    #                     in Tenent, not in IAM's config).
    tenant_resolver: Literal["template", "control_plane"] = "template"
    control_plane_base_url: str | None = None
    control_plane_timeout: float = 5.0

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
