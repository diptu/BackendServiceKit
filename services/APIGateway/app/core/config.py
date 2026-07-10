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
    redis_tenant_cache_ttl: int = 300  # 5 min: tenant detail responses
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
    tenent_base_url: str = "http://localhost:8005"
    tenant_provisioning_base_url: str = "http://localhost:8003"
    observability_management_base_url: str = "http://localhost:8020"
    organization_management_base_url: str = "http://localhost:8021"
    iam_base_url: str = "http://localhost:8022"
    user_base_url: str = "http://localhost:8023"
    authentication_base_url: str = "http://localhost:8024"
    redis_tenent_cache_ttl: int = 300  # 5 min: tenant + lifecycle GET responses
    redis_isolation_cache_ttl: int = 60  # 1 min: isolation decision responses
    redis_provisioning_cache_ttl: int = 30
    upstream_timeout: float = 30.0

    # Kong API Gateway
    kong_admin_url: str = "http://localhost:8001"
    kong_enabled: bool = True

    # Tenant Resolver (Siloed multi-tenancy — subdomain routing)
    #
    # Opt-in. When enabled, the gateway extracts the subdomain from the Host
    # header (everything left of `gateway_base_domain`) and resolves it to a
    # tenant via the Tenent Control Plane. That subdomain-derived tenant is the
    # routing boundary: it becomes the authoritative X-Tenant-ID for pre-auth
    # requests, and an authenticated request whose JWT tenant differs from the
    # subdomain's tenant is rejected (403). Unknown subdomain → 404; Control
    # Plane unreachable → 503 (fail closed — never route with an unresolved
    # tenant). Off by default, so behaviour is unchanged until configured.
    tenant_resolver_enabled: bool = False
    gateway_base_domain: str | None = None  # e.g. "my-site.com"
    control_plane_base_url: str = "http://localhost:8005"  # Tenent
    control_plane_timeout: float = 5.0
    tenant_resolver_reserved_subdomains: list[str] = Field(
        default_factory=lambda: ["www", "api", "app", "admin"]
    )

    # Security — secret_key/jwt_algorithm/jwt_issuer must match Authentication's
    # own config exactly: this is the shared-secret HS256 verification side of
    # the tokens that service issues (see services/Authentication/TODO.md on
    # why this should move to asymmetric RS256 signing eventually).
    secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "nutratenant-authentication"

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8005",  # Tenent
            "http://localhost:8003",  # TenantProvisioning
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
