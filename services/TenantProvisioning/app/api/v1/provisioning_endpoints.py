"""Provisioning REST endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGINATION_LIMIT, MAX_PAGINATION_LIMIT
from app.core.openapi import RESPONSES_READ, RESPONSES_WRITE
from app.infrastructure.database.dependencies import get_db
from app.middleware.auth import verify_token
from app.middleware.rate_limit import limiter
from app.schemas.provisioning import (
    AddResourceRequest,
    JobListResponse,
    JobResponse,
    JobSummary,
    ResourceResponse,
    RetryRequest,
    StartProvisioningRequest,
    TenantProvisioningStatusResponse,
)
from app.services.provisioning_service import ProvisioningService

if TYPE_CHECKING:
    from app.models.provisioning_job import ProvisioningJob

router = APIRouter(
    prefix="/provisioning",
    tags=["Provisioning"],
    dependencies=[Depends(verify_token)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _svc(db: DbDep, request: Request) -> ProvisioningService:
    publisher: Any = getattr(request.app.state, "publisher", None)
    return ProvisioningService(db, publisher=publisher)


SvcDep = Annotated[ProvisioningService, Depends(_svc)]


@router.post(
    "/tenants",
    response_model=JobResponse,
    status_code=201,
    responses=RESPONSES_WRITE,
    summary="Start provisioning a tenant",
)
@limiter.limit("30/minute")
async def start_provisioning(
    request: Request,
    body: StartProvisioningRequest,
    svc: SvcDep,
) -> ProvisioningJob:
    return await svc.start_provisioning(body.tenant_id, metadata=body.metadata)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List provisioning jobs",
)
async def list_jobs(
    svc: SvcDep,
    request: Request,
    tenant_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    next_cursor: str | None = Query(default=None),
    limit: int = Query(
        default=DEFAULT_PAGINATION_LIMIT, ge=1, le=MAX_PAGINATION_LIMIT
    ),
) -> JobListResponse:
    page = await svc.list_jobs(
        tenant_id=tenant_id,
        status=status,
        next_cursor=next_cursor,
        limit=limit,
    )
    return JobListResponse(
        items=[JobSummary.model_validate(j) for j in page.items],
        total=page.total,
        has_more=page.has_more,
        next_cursor=page.next_cursor,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses=RESPONSES_READ,
    summary="Get a provisioning job by ID",
)
async def get_job(job_id: UUID, svc: SvcDep, request: Request) -> JobResponse:
    from app.infrastructure.cache.redis_cache import cache_get, cache_set, job_cache_key

    key = job_cache_key(str(job_id))
    cached = await cache_get(key)
    if cached is not None:
        return JobResponse(**cached)

    job = await svc.get_job(job_id)
    resp = JobResponse.model_validate(job)
    ttl = 300 if job.status in ("completed", "failed") else 30
    await cache_set(key, resp.model_dump(mode="json"), ttl=ttl)
    return resp


@router.post(
    "/tenants/{tenant_id}/retry",
    response_model=JobResponse,
    status_code=202,
    responses=RESPONSES_WRITE,
    summary="Retry a failed provisioning job",
)
@limiter.limit("10/minute")
async def retry_provisioning(
    tenant_id: UUID,
    request: Request,
    body: RetryRequest,
    svc: SvcDep,
) -> ProvisioningJob:
    return await svc.retry_provisioning(tenant_id)


@router.post(
    "/tenants/{tenant_id}/resources",
    response_model=ResourceResponse,
    status_code=201,
    responses=RESPONSES_READ,
    summary="Manually register a provisioned resource",
)
async def add_resource(
    tenant_id: UUID,
    body: AddResourceRequest,
    svc: SvcDep,
    request: Request,
) -> ResourceResponse:
    resource = await svc.add_resource(
        tenant_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        status=body.status,
        meta=body.meta,
    )
    return ResourceResponse.model_validate(resource)


@router.get(
    "/tenants/{tenant_id}/status",
    response_model=TenantProvisioningStatusResponse,
    responses=RESPONSES_READ,
    summary="Get current provisioning status for a tenant",
)
async def get_tenant_status(
    tenant_id: UUID,
    svc: SvcDep,
    request: Request,
) -> TenantProvisioningStatusResponse:
    latest, resources = await svc.get_tenant_status(tenant_id)
    return TenantProvisioningStatusResponse(
        tenant_id=tenant_id,
        latest_job=JobResponse.model_validate(latest) if latest else None,
        resources=[ResourceResponse.model_validate(r) for r in resources],
    )
