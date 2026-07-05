"""Platform Invitation endpoints.

Mounted at /api/v1/platform-invitations, not README's literal /invitations
— OrganizationManagement already owns /api/v1/invitations/accept for its
own (different) org-level invitations, and APIGateway's route registry does
plain string-prefix matching with no path templating, so the two would
collide. See TODO.md.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import InvitationServiceDep, TenantIdDep
from app.domain.commands import AcceptInvitationCmd, CreateInvitationCmd
from app.domain.exceptions import InvitationInvalidError, InvitationNotFoundError
from app.schemas.invitation import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    CreateInvitationResponse,
    InvitationListResponse,
    InvitationResponse,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/platform-invitations", tags=["Platform Invitations"])


@router.post("", response_model=CreateInvitationResponse, status_code=201)
async def create_invitation(
    body: CreateInvitationRequest, tenant_id: TenantIdDep, svc: InvitationServiceDep
) -> CreateInvitationResponse:
    cmd = CreateInvitationCmd(
        email=body.email,
        invited_by=body.invited_by,
        expires_in_days=body.expires_in_days,
    )
    invitation, raw_token = await svc.create_invitation(tenant_id, cmd)
    return CreateInvitationResponse(
        **InvitationResponse.model_validate(invitation).model_dump(), token=raw_token
    )


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    tenant_id: TenantIdDep,
    svc: InvitationServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> InvitationListResponse:
    page = await svc.list_invitations(tenant_id, cursor=cursor, limit=limit)
    return InvitationListResponse(
        items=[InvitationResponse.model_validate(i) for i in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post("/{invitation_id}/revoke", response_model=InvitationResponse)
async def revoke_invitation(
    invitation_id: UUID, tenant_id: TenantIdDep, svc: InvitationServiceDep
) -> InvitationResponse:
    try:
        invitation = await svc.revoke_invitation(tenant_id, invitation_id)
    except InvitationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvitationInvalidError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return InvitationResponse.model_validate(invitation)


@router.post("/accept", response_model=UserResponse)
async def accept_invitation(
    body: AcceptInvitationRequest, svc: InvitationServiceDep
) -> UserResponse:
    cmd = AcceptInvitationCmd(
        token=body.token, first_name=body.first_name, last_name=body.last_name
    )
    try:
        user = await svc.accept_invitation(cmd)
    except InvitationInvalidError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(user)
