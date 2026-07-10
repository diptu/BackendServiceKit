"""Tenant provisioning endpoints.

The physical side of Siloed multi-tenancy: create + migrate + register a
tenant's own database. Trust boundary: internal-only — this is driven by
Tenent's lifecycle (provisioning state), not the public gateway.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.dependencies import ProvisioningServiceDep
from app.domain.commands import ProvisionTenantCmd
from app.models.provisioning_job import ProvisioningJob
from app.schemas.provisioning import (
    ProvisioningJobListResponse,
    ProvisioningJobResponse,
    ProvisionRequest,
)

router = APIRouter(prefix="/provisioning/tenants", tags=["Provisioning"])


def _to_response(job: ProvisioningJob) -> ProvisioningJobResponse:
    return ProvisioningJobResponse.model_validate(job)


@router.post("", response_model=ProvisioningJobResponse, status_code=201)
async def provision_tenant(
    body: ProvisionRequest, svc: ProvisioningServiceDep
) -> ProvisioningJobResponse:
    cmd = ProvisionTenantCmd(
        tenant_id=body.tenant_id, subdomain=body.subdomain, region=body.region
    )
    job = await svc.provision(cmd)
    return _to_response(job)


@router.get("", response_model=ProvisioningJobListResponse)
async def list_jobs(
    svc: ProvisioningServiceDep,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> ProvisioningJobListResponse:
    page = await svc.list(status=status, cursor=cursor, limit=limit)
    return ProvisioningJobListResponse(
        items=[_to_response(j) for j in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{tenant_id}", response_model=ProvisioningJobResponse)
async def get_job(
    tenant_id: UUID, svc: ProvisioningServiceDep
) -> ProvisioningJobResponse:
    return _to_response(await svc.get(tenant_id))


@router.post("/{tenant_id}/retry", response_model=ProvisioningJobResponse)
async def retry_job(
    tenant_id: UUID, svc: ProvisioningServiceDep
) -> ProvisioningJobResponse:
    return _to_response(await svc.retry(tenant_id))


@router.delete("/{tenant_id}", response_model=ProvisioningJobResponse)
async def deprovision_tenant(
    tenant_id: UUID, svc: ProvisioningServiceDep
) -> ProvisioningJobResponse:
    return _to_response(await svc.deprovision(tenant_id))
