"""Control Plane endpoints — the tenant → database registry that powers Siloed
multi-tenancy.

Trust boundary: every route here is **internal-only**. `POST /connections`
registers where a tenant's data lives and `GET .../dsn` returns a live
credential — neither must ever be exposed through the public gateway (same
caveat as Authentication's `/auth/credentials`). `GET /resolve` is what the
gateway's Tenant Resolver calls to turn a subdomain into a tenant, and returns
no credentials.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import ControlPlaneServiceDep
from app.domain.exceptions import (
    SubdomainConflictError,
    SubdomainNotFoundError,
    TenantConnectionNotFoundError,
    TenantSecretUnavailableError,
)
from app.schemas.control_plane import (
    ConnectionResponse,
    DsnResponse,
    RegisterConnectionRequest,
    SubdomainResolveResponse,
)

router = APIRouter(prefix="/control-plane", tags=["Control Plane"])


@router.post(
    "/connections/{tenant_id}", response_model=ConnectionResponse, status_code=201
)
async def register_connection(
    tenant_id: UUID,
    body: RegisterConnectionRequest,
    svc: ControlPlaneServiceDep,
) -> ConnectionResponse:
    try:
        connection = await svc.register(
            tenant_id,
            subdomain=body.subdomain,
            db_host=body.db_host,
            db_name=body.db_name,
            db_user=body.db_user,
            db_driver=body.db_driver,
            db_port=body.db_port,
            secret_ref=body.secret_ref,
            region=body.region,
            status=body.status,
        )
    except SubdomainConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConnectionResponse.model_validate(connection)


@router.get("/resolve", response_model=SubdomainResolveResponse)
async def resolve_subdomain(
    svc: ControlPlaneServiceDep,
    subdomain: str = Query(..., min_length=1, max_length=63),
) -> SubdomainResolveResponse:
    """Gateway Tenant Resolver entry point: subdomain → tenant. No credentials."""
    try:
        connection = await svc.resolve_subdomain(subdomain)
    except SubdomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SubdomainResolveResponse(
        tenant_id=connection.tenant_id,
        subdomain=connection.subdomain,
        status=connection.status,
    )


@router.get("/connections/{tenant_id}", response_model=ConnectionResponse)
async def get_connection(
    tenant_id: UUID, svc: ControlPlaneServiceDep
) -> ConnectionResponse:
    try:
        connection = await svc.get_connection(tenant_id)
    except TenantConnectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConnectionResponse.model_validate(connection)


@router.get("/connections/{tenant_id}/dsn", response_model=DsnResponse)
async def get_connection_dsn(
    tenant_id: UUID, svc: ControlPlaneServiceDep
) -> DsnResponse:
    """Assemble the tenant's full connection string (credential included).
    Internal-only — this is what a service's ControlPlaneConnectionResolver
    calls; it must never be reachable through the public gateway."""
    try:
        dsn = await svc.build_dsn(tenant_id)
    except TenantConnectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TenantSecretUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DsnResponse(dsn=dsn)


@router.delete("/connections/{tenant_id}", status_code=204)
async def deprovision_connection(tenant_id: UUID, svc: ControlPlaneServiceDep) -> None:
    """Disable a tenant's Control Plane record so nothing routes to it. The
    physical database drop/archive is a separate deployment step."""
    try:
        await svc.deprovision(tenant_id)
    except TenantConnectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
