"""Fleet health domain router — mounted at /api/v1/health (unchanged
prefix, see TODO.md Decision #1). Registry shrank to Tenent + APIGateway +
self (Decision #5)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import require_operator_scope
from app.domains.health.dependencies import get_health_service
from app.domains.health.exceptions import UnknownServiceError
from app.domains.health.schemas.health import (
    DependencyCrossCutEntry,
    DependencyCrossCutResponse,
    FleetHealthDetailResponse,
    FleetHealthResponse,
    LivenessEntry,
    LivenessListResponse,
    ServiceHealthResponse,
    VersionEntry,
    VersionsResponse,
)
from app.domains.health.services.health_service import HealthService

router = APIRouter(
    prefix="/health",
    tags=["Fleet Health"],
    dependencies=[Depends(require_operator_scope)],
)

HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
ServiceQuery = Annotated[str | None, Query(alias="service")]


@router.get("/dependencies", response_model=FleetHealthResponse)
async def get_dependencies(service: HealthServiceDep) -> FleetHealthResponse:
    fleet = await service.get_fleet_health()
    return FleetHealthResponse.from_domain(fleet)


@router.get("/version", response_model=VersionsResponse)
async def get_versions(service: HealthServiceDep) -> VersionsResponse:
    fleet = await service.get_fleet_health()
    items = [VersionEntry(service=s.name, version=s.version) for s in fleet.services]
    return VersionsResponse(items=items, count=len(items))


@router.get("/live", response_model=LivenessListResponse)
async def get_liveness(
    health_service: HealthServiceDep, target: ServiceQuery = None
) -> LivenessListResponse:
    if target is not None:
        result = await health_service.get_service_health(target)
        if result is None:
            raise UnknownServiceError(target)
        items = [
            LivenessEntry(service=result.name, reachable=result.reachable, version=result.version)
        ]
        return LivenessListResponse(items=items, count=1)

    fleet = await health_service.get_fleet_health()
    items = [
        LivenessEntry(service=s.name, reachable=s.reachable, version=s.version)
        for s in fleet.services
    ]
    return LivenessListResponse(items=items, count=len(items))


@router.get("/ready", response_model=FleetHealthResponse)
async def get_readiness(
    health_service: HealthServiceDep, target: ServiceQuery = None
) -> FleetHealthResponse:
    if target is not None:
        result = await health_service.get_service_health(target)
        if result is None:
            raise UnknownServiceError(target)
        return FleetHealthResponse(
            overall_status="healthy" if result.reachable else "unhealthy",
            services=[ServiceHealthResponse.from_domain(result)],
        )
    fleet = await health_service.get_fleet_health()
    return FleetHealthResponse.from_domain(fleet)


@router.get("/startup", response_model=FleetHealthResponse)
async def get_startup(
    health_service: HealthServiceDep, target: ServiceQuery = None
) -> FleetHealthResponse:
    """Alias of /ready — none of the merged domains have a meaningfully
    separate startup phase."""
    return await get_readiness(health_service, target)


@router.get("/database", response_model=DependencyCrossCutResponse)
async def get_database_health(service: HealthServiceDep) -> DependencyCrossCutResponse:
    return await _cross_cut(service, "database", "postgres", "pg", "database")


@router.get("/cache", response_model=DependencyCrossCutResponse)
async def get_cache_health(service: HealthServiceDep) -> DependencyCrossCutResponse:
    return await _cross_cut(service, "cache", "redis", "cache")


@router.get("/message-broker", response_model=DependencyCrossCutResponse)
async def get_message_broker_health(service: HealthServiceDep) -> DependencyCrossCutResponse:
    return await _cross_cut(service, "message-broker", "rabbitmq", "broker", "queue")


@router.get("/details", response_model=FleetHealthDetailResponse)
async def get_details(service: HealthServiceDep) -> FleetHealthDetailResponse:
    fleet = await service.get_fleet_health()
    return FleetHealthDetailResponse.from_domain(fleet)


async def _cross_cut(
    service: HealthService, label: str, *needles: str
) -> DependencyCrossCutResponse:
    matches = await service.filter_by_dependency(*needles)
    items = [
        DependencyCrossCutEntry(
            service=name, status=dep.status, latency_ms=dep.latency_ms, error=dep.error
        )
        for name, dep in matches
    ]
    return DependencyCrossCutResponse(dependency=label, items=items, count=len(items))
