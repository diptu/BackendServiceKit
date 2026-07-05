"""Pydantic schemas for Organization Membership endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import MembershipRole, MembershipStatus
from app.schemas.base import AppBaseModel


class AddMemberRequest(AppBaseModel):
    user_id: UUID
    role: MembershipRole = MembershipRole.MEMBER


class UpdateMemberRoleRequest(AppBaseModel):
    role: MembershipRole


class MembershipResponse(AppBaseModel):
    id: UUID
    organization_id: UUID
    tenant_id: UUID
    user_id: UUID
    role: MembershipRole
    status: MembershipStatus
    invited_by: UUID | None
    created_at: datetime
    updated_at: datetime


class MembershipListResponse(AppBaseModel):
    items: list[MembershipResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = Field(default=False)
