"""Central application configuration — merged from TenantManagement, TenantLifecycle, TenantIsolation."""

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
    app_name: str = "nutratenant-tenent"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_tenant",
    )
    database_ssl: bool = Field(default=False)
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379/1"

    # Messaging
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "tenant.events"

    # Security / JWT (from TenantIsolation)
    secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_auth_enabled: bool = False

    # External services
    tenant_provisioning_base_url: str = "http://localhost:8003"
    tenant_provisioning_timeout: float = 5.0

    # Control Plane (Siloed multi-tenancy — see TODO.md)
    #
    # When `control_plane_auto_register` is on, entering the `provisioning`
    # lifecycle state registers the tenant's database home in the Control Plane
    # from these templates (`{tenant}` = tenant hex id, `{name}` = tenant slug),
    # and offboarding disables it. Off by default so existing behaviour is
    # unchanged. Credentials are never taken here — only a `secret_ref`.
    control_plane_auto_register: bool = False
    tenant_db_driver: str = "postgresql+asyncpg"
    tenant_db_host: str = "localhost"
    tenant_db_port: int = 5432
    tenant_db_user: str = "postgres"
    tenant_db_name_template: str = "tenant_{tenant}"
    tenant_subdomain_template: str = "{name}"
    tenant_db_secret_ref_template: str | None = None

    # Rate limiting
    rate_limit_enabled: bool = True
    default_rate_limit: str = "100/minute"

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8000",  # APIGateway
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
