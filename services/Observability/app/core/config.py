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
    app_name: str = "nutratenant-observability"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    sibling_timeout: float = 5.0

    # The six composed services — TODO.md Decision #1/#11: this service
    # holds no credentials of its own and never calls a tier-1 backend
    # (Loki/Tempo/Prometheus/Alertmanager/Pushgateway) directly.
    logging_base_url: str = "http://localhost:8006"
    distributed_tracing_base_url: str = "http://localhost:8007"
    metrics_collection_base_url: str = "http://localhost:8008"
    monitoring_base_url: str = "http://localhost:8009"
    alerting_base_url: str = "http://localhost:8010"
    health_check_base_url: str = "http://localhost:8011"

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

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = True
    otlp_endpoint: str = "http://localhost:4317"
    healthcheck_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
