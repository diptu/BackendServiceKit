"""Central application configuration — superset of all seven merged
services' settings. See TODO.md Decision #1."""

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
    app_name: str = "nutratenant-observability-management"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    sibling_timeout: float = 5.0

    # Tier-1 raw backends — one shared httpx client per backend (Decision #3)
    loki_base_url: str = "http://localhost:3100"
    tempo_base_url: str = "http://localhost:3200"
    prometheus_base_url: str = "http://localhost:9090"
    pushgateway_base_url: str = "http://localhost:9091"
    alertmanager_base_url: str = "http://localhost:9093"

    # External services still out-of-process — unaffected by this merge
    tenent_base_url: str = "http://localhost:8005"
    api_gateway_base_url: str = "http://localhost:8080"

    # Alerting domain
    managed_rules_file_path: str = "/data/rules/managed.yml"
    managed_rules_group_name: str = "alerting-service-managed"
    default_acknowledge_minutes: int = 240

    # Observability domain
    default_window_minutes: float = 15.0

    # Security / JWT
    secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_auth_enabled: bool = False

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8080",  # APIGateway
        ]
    )

    # Observability (self)
    enable_metrics: bool = True
    enable_tracing: bool = True
    otlp_endpoint: str = "http://localhost:4317"
    healthcheck_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
