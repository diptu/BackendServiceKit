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
    app_name: str = "nutratenant-tenant-provisioning"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database (this service's own global job store — NOT per-tenant)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_provisioning",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # ---------------------------------------------------------------------
    # Provisioning — the physical side of Siloed multi-tenancy
    # ---------------------------------------------------------------------
    # How a tenant's database is physically created:
    #   "local"    — dev/test: a per-tenant SQLite file (no CREATE DATABASE)
    #   "postgres" — connect to admin_database_url and run CREATE DATABASE
    provisioner_backend: Literal["local", "postgres"] = "local"
    # Admin/maintenance connection used to CREATE/DROP tenant databases.
    admin_database_url: str | None = None
    # Template for each tenant's database URL; {tenant} = tenant hex id.
    tenant_database_url_template: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/tenant_{tenant}"
    )
    # Local backend dir for the SQLite files it creates (dev/test).
    local_provisioner_dir: str = "/tmp/nutratenant-tenants"

    # Services whose schema must be migrated into every new tenant database.
    managed_services: list[str] = Field(
        default_factory=lambda: [
            "IAM",
            "Authentication",
            "User",
            "OrganizationManagement",
            "SessionManagemet",
        ]
    )

    # Control Plane (Tenent) — where the provisioned connection is registered.
    control_plane_base_url: str = "http://localhost:8005"
    control_plane_timeout: float = 5.0
    control_plane_register_enabled: bool = True

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8080",  # APIGateway
        ]
    )

    # Observability
    enable_metrics: bool = True
    healthcheck_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
