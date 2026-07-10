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
    app_name: str = "nutratenant-authentication"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_authentication",
    )
    database_ssl: bool = Field(default=False)
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # ---------------------------------------------------------------------
    # Siloed multi-tenancy (database-per-tenant) — opt-in; default OFF keeps
    # shared-schema. IAM is the reference implementation (services/IAM/TODO.md).
    # ---------------------------------------------------------------------
    siloed_multitenancy_enabled: bool = False
    tenant_database_url_template: str | None = None
    tenant_database_overrides: dict[str, str] = Field(default_factory=dict)
    tenant_max_engines: int | None = None
    tenant_resolver: Literal["template", "control_plane"] = "template"
    control_plane_base_url: str | None = None
    control_plane_timeout: float = 5.0

    # JWT / tokens — HS256 with a shared secret matches the claim shape
    # Tenent's IsolationService.resolve_context already expects to decode
    # (tenant_id/user_id/scopes).
    #
    # RS256 (asymmetric) is now supported: set `jwt_algorithm=RS256` plus a
    # PEM `jwt_private_key`/`jwt_public_key` pair and only this service holds
    # the private key — every other service verifies with the public key it
    # fetches from `GET /.well-known/jwks.json`. HS256 stays the default so
    # existing shared-secret consumers keep working until they migrate.
    secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_private_key: str | None = None  # PEM; required when jwt_algorithm=RS256
    jwt_public_key: str | None = None  # PEM; required when jwt_algorithm=RS256
    jwt_issuer: str = "nutratenant-authentication"
    access_token_ttl_seconds: int = 900  # 15 minutes
    refresh_token_ttl_seconds: int = 1_209_600  # 14 days

    # MFA (TOTP)
    mfa_issuer_name: str = "NutraTenant"  # label shown in authenticator apps
    mfa_recovery_code_count: int = 10
    mfa_challenge_ttl_seconds: int = 300  # 5 min to complete step-up after login

    # OAuth2.1 (this service acts as the authorization server)
    oauth_authorization_code_ttl_seconds: int = 60  # short-lived, single-use
    oauth_default_scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile"]
    )

    # SSO / OIDC (this service acts as a relying party to an external IdP)
    sso_state_ttl_seconds: int = 600
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_authorization_endpoint: str | None = None
    oidc_token_endpoint: str | None = None
    oidc_jwks_uri: str | None = None
    oidc_redirect_uri: str | None = None

    # Account lockout (brute-force protection)
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15

    # Rate limiting
    rate_limit_enabled: bool = True
    login_rate_limit: str = "5/minute"

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
