"""Organizations CRUD + settings/stats/sub-resource-enumeration endpoints.

Implements every endpoint documented in services/OrganizationManagement/README.md,
plus membership/team/invitation/audit-trail/settings-history endpoints added
per the /org-service skill review (see TODO.md).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import (
    InvitationServiceDep,
    MembershipServiceDep,
    OrganizationDep,
    OrganizationServiceDep,
    TeamServiceDep,
    TenantIdDep,
)
from app.domain.commands import (
    AcceptInvitationCmd,
    AddMemberCmd,
    CreateInvitationCmd,
    CreateOrganizationCmd,
    CreateTeamCmd,
    UpdateOrganizationCmd,
    UpdateOrganizationSettingsCmd,
    UpdateTeamCmd,
)
from app.domain.exceptions import (
    InvalidParentTeamError,
    InvitationInvalidError,
    InvitationNotFoundError,
    MembershipAlreadyExistsError,
    MembershipNotFoundError,
    OrganizationDeletedError,
    OrganizationSlugConflictError,
    TeamMembershipAlreadyExistsError,
    TeamMembershipNotFoundError,
    TeamNameConflictError,
    TenantNotFoundError,
    TenantServiceUnavailableError,
)
from app.schemas.event import OrganizationEventListResponse, OrganizationEventResponse
from app.schemas.invitation import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    CreateInvitationResponse,
    InvitationListResponse,
    InvitationResponse,
)
from app.schemas.membership import (
    AddMemberRequest,
    MembershipListResponse,
    MembershipResponse,
    UpdateMemberRoleRequest,
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
from app.schemas.settings_history import (
    OrganizationSettingsHistoryListResponse,
    OrganizationSettingsHistoryResponse,
)
from app.schemas.team import (
    AddTeamMemberRequest,
    CreateTeamRequest,
    TeamListResponse,
    TeamMemberListResponse,
    TeamResponse,
    UpdateTeamRequest,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])
invitations_router = APIRouter(prefix="/invitations", tags=["Invitations"])


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


@router.get(
    "/{organization_id}/settings/history",
    response_model=OrganizationSettingsHistoryListResponse,
)
async def get_organization_settings_history(
    organization: OrganizationDep,
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> OrganizationSettingsHistoryListResponse:
    page = await svc.list_settings_history(
        organization.id, tenant_id, limit=limit, offset=offset
    )
    return OrganizationSettingsHistoryListResponse(
        items=[
            OrganizationSettingsHistoryResponse.model_validate(h) for h in page.items
        ],
        total=page.total,
        has_more=page.has_more,
    )


@router.get("/{organization_id}/events", response_model=OrganizationEventListResponse)
async def list_organization_events(
    organization: OrganizationDep,
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> OrganizationEventListResponse:
    page = await svc.list_events(organization.id, tenant_id, cursor=cursor, limit=limit)
    return OrganizationEventListResponse(
        items=[OrganizationEventResponse.model_validate(e) for e in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/members", response_model=MembershipListResponse)
async def list_organization_members(
    organization: OrganizationDep,
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> MembershipListResponse:
    page = await svc.list_members(
        organization.id, tenant_id, cursor=cursor, limit=limit
    )
    return MembershipListResponse(
        items=[MembershipResponse.model_validate(m) for m in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/{organization_id}/members", response_model=MembershipResponse, status_code=201
)
async def add_organization_member(
    organization: OrganizationDep,
    body: AddMemberRequest,
    tenant_id: TenantIdDep,
    svc: MembershipServiceDep,
) -> MembershipResponse:
    cmd = AddMemberCmd(user_id=body.user_id, role=body.role)
    try:
        membership = await svc.add_member(organization.id, tenant_id, cmd)
    except MembershipAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MembershipResponse.model_validate(membership)


@router.patch("/{organization_id}/members/{user_id}", response_model=MembershipResponse)
async def update_organization_member_role(
    organization: OrganizationDep,
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    tenant_id: TenantIdDep,
    svc: MembershipServiceDep,
) -> MembershipResponse:
    try:
        membership = await svc.update_role(
            organization.id, tenant_id, user_id, body.role
        )
    except MembershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MembershipResponse.model_validate(membership)


@router.delete("/{organization_id}/members/{user_id}", status_code=204)
async def remove_organization_member(
    organization: OrganizationDep,
    user_id: UUID,
    tenant_id: TenantIdDep,
    svc: MembershipServiceDep,
) -> None:
    try:
        await svc.remove_member(organization.id, tenant_id, user_id)
    except MembershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Workspaces — no owning service exists yet anywhere in this repo
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/workspaces", response_model=SubResourceListResponse)
async def list_organization_workspaces(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> SubResourceListResponse:
    return SubResourceListResponse.model_validate(
        await svc.list_workspaces(organization.id, tenant_id)
    )


# ---------------------------------------------------------------------------
# Teams / Departments
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/teams", response_model=TeamListResponse)
async def list_organization_teams(
    organization: OrganizationDep,
    tenant_id: TenantIdDep,
    svc: OrganizationServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> TeamListResponse:
    page = await svc.list_teams(organization.id, tenant_id, cursor=cursor, limit=limit)
    return TeamListResponse(
        items=[TeamResponse.model_validate(t) for t in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post("/{organization_id}/teams", response_model=TeamResponse, status_code=201)
async def create_organization_team(
    organization: OrganizationDep,
    body: CreateTeamRequest,
    tenant_id: TenantIdDep,
    svc: TeamServiceDep,
) -> TeamResponse:
    cmd = CreateTeamCmd(
        name=body.name,
        team_type=body.team_type,
        description=body.description,
        parent_team_id=body.parent_team_id,
    )
    try:
        team = await svc.create_team(organization.id, tenant_id, cmd)
    except TeamNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidParentTeamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TeamResponse.model_validate(team)


@router.get("/{organization_id}/teams/{team_id}", response_model=TeamResponse)
async def get_organization_team(
    organization: OrganizationDep, team_id: UUID, svc: TeamServiceDep
) -> TeamResponse:
    team = await svc.get(organization.id, team_id)
    return TeamResponse.model_validate(team)


@router.patch("/{organization_id}/teams/{team_id}", response_model=TeamResponse)
async def update_organization_team(
    organization: OrganizationDep,
    team_id: UUID,
    body: UpdateTeamRequest,
    tenant_id: TenantIdDep,
    svc: TeamServiceDep,
) -> TeamResponse:
    cmd = UpdateTeamCmd(name=body.name, description=body.description)
    try:
        team = await svc.update_team(organization.id, tenant_id, team_id, cmd)
    except TeamNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TeamResponse.model_validate(team)


@router.delete("/{organization_id}/teams/{team_id}", status_code=204)
async def delete_organization_team(
    organization: OrganizationDep,
    team_id: UUID,
    tenant_id: TenantIdDep,
    svc: TeamServiceDep,
) -> None:
    await svc.delete_team(organization.id, tenant_id, team_id)


@router.get(
    "/{organization_id}/teams/{team_id}/members", response_model=TeamMemberListResponse
)
async def list_organization_team_members(
    organization: OrganizationDep, team_id: UUID, svc: TeamServiceDep
) -> TeamMemberListResponse:
    member_ids = await svc.list_team_members(organization.id, team_id)
    return TeamMemberListResponse(items=member_ids, total=len(member_ids))


@router.post("/{organization_id}/teams/{team_id}/members", status_code=204)
async def add_organization_team_member(
    organization: OrganizationDep,
    team_id: UUID,
    body: AddTeamMemberRequest,
    tenant_id: TenantIdDep,
    svc: TeamServiceDep,
) -> None:
    try:
        await svc.add_team_member(organization.id, tenant_id, team_id, body.user_id)
    except TeamMembershipAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{organization_id}/teams/{team_id}/members/{user_id}", status_code=204)
async def remove_organization_team_member(
    organization: OrganizationDep,
    team_id: UUID,
    user_id: UUID,
    tenant_id: TenantIdDep,
    svc: TeamServiceDep,
) -> None:
    try:
        await svc.remove_team_member(organization.id, tenant_id, team_id, user_id)
    except TeamMembershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Groups — deliberately left as a stub; see TODO.md
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/groups", response_model=SubResourceListResponse)
async def list_organization_groups(
    organization: OrganizationDep, tenant_id: TenantIdDep, svc: OrganizationServiceDep
) -> SubResourceListResponse:
    return SubResourceListResponse.model_validate(
        await svc.list_groups(organization.id, tenant_id)
    )


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post(
    "/{organization_id}/invitations",
    response_model=CreateInvitationResponse,
    status_code=201,
)
async def create_organization_invitation(
    organization: OrganizationDep,
    body: CreateInvitationRequest,
    tenant_id: TenantIdDep,
    svc: InvitationServiceDep,
) -> CreateInvitationResponse:
    cmd = CreateInvitationCmd(
        email=body.email,
        invited_by=body.invited_by,
        role=body.role,
        expires_in_days=body.expires_in_days,
    )
    invitation, raw_token = await svc.create_invitation(organization.id, tenant_id, cmd)
    return CreateInvitationResponse(
        **InvitationResponse.model_validate(invitation).model_dump(), token=raw_token
    )


@router.get("/{organization_id}/invitations", response_model=InvitationListResponse)
async def list_organization_invitations(
    organization: OrganizationDep,
    svc: InvitationServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> InvitationListResponse:
    page = await svc.list_invitations(organization.id, cursor=cursor, limit=limit)
    return InvitationListResponse(
        items=[InvitationResponse.model_validate(i) for i in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/{organization_id}/invitations/{invitation_id}/revoke",
    response_model=InvitationResponse,
)
async def revoke_organization_invitation(
    organization: OrganizationDep,
    invitation_id: UUID,
    tenant_id: TenantIdDep,
    svc: InvitationServiceDep,
) -> InvitationResponse:
    try:
        invitation = await svc.revoke_invitation(
            organization.id, tenant_id, invitation_id
        )
    except InvitationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvitationInvalidError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return InvitationResponse.model_validate(invitation)


@invitations_router.post("/accept", response_model=MembershipResponse)
async def accept_invitation(
    body: AcceptInvitationRequest, svc: InvitationServiceDep
) -> MembershipResponse:
    cmd = AcceptInvitationCmd(token=body.token, user_id=body.user_id)
    try:
        membership = await svc.accept_invitation(cmd)
    except InvitationInvalidError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MembershipAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MembershipResponse.model_validate(membership)
