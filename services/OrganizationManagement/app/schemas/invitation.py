"""Pydantic schemas for Invitation endpoints.

Note: the raw token only ever appears in CreateInvitationResponse (returned
once, at creation) and AcceptInvitationRequest (submitted by the invitee).
InvitationResponse deliberately has no token/token_hash field.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import InvitationStatus, MembershipRole
from app.schemas.base import AppBaseModel


class CreateInvitationRequest(AppBaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role: MembershipRole = MembershipRole.MEMBER
    invited_by: UUID
    expires_in_days: int = Field(7, ge=1, le=90)


class InvitationResponse(AppBaseModel):
    id: UUID
    organization_id: UUID
    tenant_id: UUID
    email: str
    role: MembershipRole
    status: InvitationStatus
    invited_by: UUID
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class CreateInvitationResponse(InvitationResponse):
    token: str = Field(..., description="Raw invitation token — shown only once.")


class InvitationListResponse(AppBaseModel):
    items: list[InvitationResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False


class AcceptInvitationRequest(AppBaseModel):
    token: str
    user_id: UUID
