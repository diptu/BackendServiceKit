"""Pydantic schemas for Role endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import EntityStatus
from app.schemas.base import AppBaseModel
from app.schemas.permission import PermissionResponse


class CreateRoleRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID header."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class UpdateRoleRequest(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class RoleResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    status: EntityStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class RoleListResponse(AppBaseModel):
    items: list[RoleResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool


class AssignPermissionRequest(AppBaseModel):
    permission_id: UUID


class RolePermissionListResponse(AppBaseModel):
    items: list[PermissionResponse]
    total: int


class AssignRoleRequest(AppBaseModel):
    role_id: UUID
