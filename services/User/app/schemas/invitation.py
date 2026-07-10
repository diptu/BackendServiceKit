"""Pydantic schemas for platform Invitation endpoints.

Note: the raw token only ever appears in CreateInvitationResponse (returned
once, at creation) and AcceptInvitationRequest (submitted by the invitee).
InvitationResponse deliberately has no token/token_hash field.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import InvitationStatus
from app.schemas.base import AppBaseModel


class CreateInvitationRequest(AppBaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    invited_by: UUID
    expires_in_days: int = Field(7, ge=1, le=90)


class InvitationResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    email: str
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
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
