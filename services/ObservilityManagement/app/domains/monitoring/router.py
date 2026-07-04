"""Monitoring domain router — mounted at /api/v1/monitoring (unchanged
prefix, see TODO.md Decision #1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_operator_scope
from app.domains.monitoring.dependencies import get_monitoring_service
from app.domains.monitoring.schemas.monitoring import (
    ClusterInfoResponse,
    ClustersResponse,
    PlatformStatusResponse,
    ResourceHealthResponse,
    ServiceHealthResponse,
    ServicesResponse,
    SummaryResponse,
    TenantSummaryResponse,
)
from app.domains.monitoring.services.monitoring_service import MonitoringService

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(require_operator_scope)],
)

MonitoringServiceDep = Annotated[MonitoringService, Depends(get_monitoring_service)]


@router.get("/status", response_model=PlatformStatusResponse)
async def get_status(service: MonitoringServiceDep) -> PlatformStatusResponse:
    status = await service.get_status()
    return PlatformStatusResponse.from_domain(status)


@router.get("/services", response_model=ServicesResponse)
async def get_services(service: MonitoringServiceDep) -> ServicesResponse:
    services = await service.get_services()
    items = [ServiceHealthResponse.from_domain(s) for s in services]
    return ServicesResponse(items=items, count=len(items))


@router.get("/services/{service_id}", response_model=ServiceHealthResponse)
async def get_service_detail(
    service_id: str, service: MonitoringServiceDep
) -> ServiceHealthResponse:
    detail = await service.get_service_detail(service_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_id!r}")
    return ServiceHealthResponse.from_domain(detail)


@router.get("/resources", response_model=ResourceHealthResponse)
async def get_resources(service: MonitoringServiceDep) -> ResourceHealthResponse:
    resources = await service.get_resources()
    return ResourceHealthResponse.from_domain(resources)


@router.get("/tenants", response_model=TenantSummaryResponse)
async def get_tenants(service: MonitoringServiceDep) -> TenantSummaryResponse:
    tenants = await service.get_tenants()
    return TenantSummaryResponse.from_domain(tenants)


@router.get("/clusters", response_model=ClustersResponse)
async def get_clusters(service: MonitoringServiceDep) -> ClustersResponse:
    clusters = service.get_clusters()
    items = [ClusterInfoResponse.from_domain(c) for c in clusters]
    return ClustersResponse(items=items, count=len(items))


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(service: MonitoringServiceDep) -> SummaryResponse:
    summary = await service.get_summary()
    return SummaryResponse(**summary)
