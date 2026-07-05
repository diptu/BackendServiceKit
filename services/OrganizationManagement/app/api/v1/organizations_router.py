"""Organizations CRUD + settings/stats/sub-resource-enumeration endpoints.

Implements every endpoint documented in services/OrganizationManagement/README.md.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import OrganizationDep, OrganizationServiceDep, TenantIdDep
from app.domain.commands import (
    CreateOrganizationCmd,
    UpdateOrganizationCmd,
    UpdateOrganizationSettingsCmd,
)
from app.domain.exceptions import (
    OrganizationDeletedError,
    OrganizationSlugConflictError,
    TenantNotFoundError,
    TenantServiceUnavailableError,
)
from app.schemas.organization import (
    CreateOrganizationRequest,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationSettingsResponse,
    OrganizationStatsResponse,
    SubResourceListResponse,
    UpdateOrganizationRequest,
    UpdateOrganizationSettingsRequest,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ---------------------------------------------------------------------------
# Core lifecycle management
# ---------------------------------------------------------------------------


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: CreateOrganizationRequest, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> OrganizationResponse:
    cmd = CreateOrganizationCmd(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
    )
    try:
        organization = await svc.create(cmd)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TenantServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OrganizationSlugConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OrganizationResponse.model_validate(organization)


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> OrganizationListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(o) for o in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(organization: OrganizationDep) -> OrganizationResponse:
    return OrganizationResponse.model_validate(organization)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization: OrganizationDep,
    body: UpdateOrganizationRequest,
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
) -> OrganizationResponse:
    cmd = UpdateOrganizationCmd(name=body.name, description=body.description)
    try:
        updated = await svc.update(organization.id, tenant_id, cmd)
    except OrganizationDeletedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OrganizationResponse.model_validate(updated)


@router.delete("/{organization_id}", status_code=204)
async def delete_organization(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> None:
    await svc.delete(organization.id, tenant_id)


# ---------------------------------------------------------------------------
# Administration & Insights
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/stats", response_model=OrganizationStatsResponse)
async def get_organization_stats(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> OrganizationStatsResponse:
    stats = await svc.get_stats(organization.id, tenant_id)
    return OrganizationStatsResponse.model_validate(stats)


@router.get("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> OrganizationSettingsResponse:
    org_settings = await svc.get_settings(organization.id, tenant_id)
    return OrganizationSettingsResponse.model_validate(org_settings)


@router.patch(
    "/{organization_id}/settings", response_model=OrganizationSettingsResponse
)
async def update_organization_settings(
    organization: OrganizationDep,
    body: UpdateOrganizationSettingsRequest,
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
) -> OrganizationSettingsResponse:
    cmd = UpdateOrganizationSettingsCmd(
        timezone=body.timezone,
        locale=body.locale,
        default_member_role=body.default_member_role,
        feature_flags=body.feature_flags,
        compliance_rules=body.compliance_rules,
    )
    org_settings = await svc.update_settings(organization.id, tenant_id, cmd)
    return OrganizationSettingsResponse.model_validate(org_settings)


# ---------------------------------------------------------------------------
# Sub-resource enumeration
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/members", response_model=SubResourceListResponse)
async def list_organization_members(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> SubResourceListResponse:
    return SubResourceListResponse.model_validate(
        await svc.list_members(organization.id, tenant_id)
    )


@router.get("/{organization_id}/workspaces", response_model=SubResourceListResponse)
async def list_organization_workspaces(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> SubResourceListResponse:
    return SubResourceListResponse.model_validate(
        await svc.list_workspaces(organization.id, tenant_id)
    )


@router.get("/{organization_id}/teams", response_model=SubResourceListResponse)
async def list_organization_teams(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> SubResourceListResponse:
    return SubResourceListResponse.model_validate(
        await svc.list_teams(organization.id, tenant_id)
    )


@router.get("/{organization_id}/groups", response_model=SubResourceListResponse)
async def list_organization_groups(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> SubResourceListResponse:
    return SubResourceListResponse.model_validate(
        await svc.list_groups(organization.id, tenant_id)
    )
