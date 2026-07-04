"""Request/response schemas for the Health domain."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.core.schema_base import APIModel
from app.domains.health.models import DependencyStatus, FleetHealth, ServiceHealth


class DependencyStatusResponse(APIModel):
    name: str
    status: str
    latency_ms: float | None = None
    error: str | None = None

    @classmethod
    def from_domain(cls, dep: DependencyStatus) -> "DependencyStatusResponse":
        return cls(name=dep.name, status=dep.status, latency_ms=dep.latency_ms, error=dep.error)


class ServiceHealthResponse(APIModel):
    name: str
    base_url: str
    reachable: bool
    version: str | None = None
    observed_uptime_seconds: float | None = None
    dependencies: list[DependencyStatusResponse] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, service: ServiceHealth) -> "ServiceHealthResponse":
        return cls(
            name=service.name,
            base_url=service.base_url,
            reachable=service.reachable,
            version=service.version,
            observed_uptime_seconds=service.observed_uptime_seconds,
            dependencies=[DependencyStatusResponse.from_domain(d) for d in service.dependencies],
        )


class ServiceHealthDetailResponse(ServiceHealthResponse):
    raw_health: dict[str, Any] | None = None
    raw_ready: dict[str, Any] | None = None

    @classmethod
    def from_domain_detail(cls, service: ServiceHealth) -> "ServiceHealthDetailResponse":
        base = ServiceHealthResponse.from_domain(service)
        return cls(**base.model_dump(), raw_health=service.raw_health, raw_ready=service.raw_ready)


class FleetHealthResponse(APIModel):
    overall_status: str
    services: list[ServiceHealthResponse]

    @classmethod
    def from_domain(cls, fleet: FleetHealth) -> "FleetHealthResponse":
        return cls(
            overall_status=fleet.overall_status,
            services=[ServiceHealthResponse.from_domain(s) for s in fleet.services],
        )


class FleetHealthDetailResponse(APIModel):
    overall_status: str
    services: list[ServiceHealthDetailResponse]

    @classmethod
    def from_domain(cls, fleet: FleetHealth) -> "FleetHealthDetailResponse":
        return cls(
            overall_status=fleet.overall_status,
            services=[ServiceHealthDetailResponse.from_domain_detail(s) for s in fleet.services],
        )


class LivenessEntry(APIModel):
    service: str
    reachable: bool
    version: str | None = None


class LivenessListResponse(APIModel):
    items: list[LivenessEntry]
    count: int


class VersionEntry(APIModel):
    service: str
    version: str | None = None


class VersionsResponse(APIModel):
    items: list[VersionEntry]
    count: int


class DependencyCrossCutEntry(APIModel):
    service: str
    status: str
    latency_ms: float | None = None
    error: str | None = None


class DependencyCrossCutResponse(APIModel):
    dependency: str
    items: list[DependencyCrossCutEntry]
    count: int
