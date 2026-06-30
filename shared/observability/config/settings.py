"""Observability settings — loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    otel_service_name: str = "unknown-service"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_exporter_otlp_protocol: str = "grpc"
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    deployment_environment: str = "development"
