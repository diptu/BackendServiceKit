"""Request/response schemas for the Monitoring domain."""

from __future__ import annotations

from pydantic import Field

from app.core.schema_base import APIModel
from app.domains.monitoring.repositories.monitoring_repository import (
    ClusterInfo,
    PlatformStatus,
    ResourceHealth,
    ServiceHealth,
    TenantSummary,
)


class ServiceHealthResponse(APIModel):
    name: str
    base_url: str
    reachable: bool
    status_code: int | None = None
    latency_ms: float | None = None
    detail: str | None = None

    @classmethod
    def from_domain(cls, service: ServiceHealth) -> "ServiceHealthResponse":
        return cls(
            name=service.name,
            base_url=service.base_url,
            reachable=service.reachable,
            status_code=service.status_code,
            latency_ms=service.latency_ms,
            detail=service.detail,
        )


class ServicesResponse(APIModel):
    items: list[ServiceHealthResponse]
    count: int


class PlatformStatusResponse(APIModel):
    overall_status: str
    services: list[ServiceHealthResponse]
    active_alert_count: int | None

    @classmethod
    def from_domain(cls, status: PlatformStatus) -> "PlatformStatusResponse":
        return cls(
            overall_status=status.overall_status,
            services=[ServiceHealthResponse.from_domain(s) for s in status.services],
            active_alert_count=status.active_alert_count,
        )


class ResourceHealthResponse(APIModel):
    postgres_reachable: bool | None
    redis_reachable: bool | None
    rabbitmq_reachable: bool | None

    @classmethod
    def from_domain(cls, resources: ResourceHealth) -> "ResourceHealthResponse":
        return cls(
            postgres_reachable=resources.postgres_reachable,
            redis_reachable=resources.redis_reachable,
            rabbitmq_reachable=resources.rabbitmq_reachable,
        )


class TenantSummaryResponse(APIModel):
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, summary: TenantSummary) -> "TenantSummaryResponse":
        return cls(total=summary.total, by_status=summary.by_status)


class ClusterInfoResponse(APIModel):
    name: str
    environment: str
    service_count: int

    @classmethod
    def from_domain(cls, cluster: ClusterInfo) -> "ClusterInfoResponse":
        return cls(
            name=cluster.name, environment=cluster.environment, service_count=cluster.service_count
        )


class ClustersResponse(APIModel):
    items: list[ClusterInfoResponse]
    count: int


class SummaryResponse(APIModel):
    overall_status: str
    services_healthy: int
    services_total: int
    tenants_total: int
    active_alert_count: int | None
