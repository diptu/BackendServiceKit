"""Pydantic schemas for Tenant Membership endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.enums import MembershipStatus
from app.schemas.base import AppBaseModel


class AddTenantMemberRequest(AppBaseModel):
    user_id: UUID


class TenantMembershipResponse(AppBaseModel):
    tenant_id: UUID
    user_id: UUID
    status: MembershipStatus
    joined_at: datetime


class TenantMembershipListResponse(AppBaseModel):
    items: list[TenantMembershipResponse]
    total: int
