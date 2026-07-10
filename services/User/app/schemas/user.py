"""Pydantic schemas for User endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import UserStatus
from app.schemas.base import AppBaseModel


class CreateUserRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID header."""

    email: str = Field(..., min_length=3, max_length=255)
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)


class UpdateUserRequest(AppBaseModel):
    email: str | None = Field(None, min_length=3, max_length=255)
    first_name: str | None = Field(None, min_length=1, max_length=255)
    last_name: str | None = Field(None, min_length=1, max_length=255)


class UserStatusTransitionRequest(AppBaseModel):
    reason: str | None = Field(None, max_length=500)
    performed_by: UUID | None = None


class LockUserRequest(AppBaseModel):
    reason: str | None = Field(None, max_length=500)
    locked_by: UUID | None = None


class UserResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    first_name: str
    last_name: str
    display_name: str
    status: UserStatus
    locked_reason: str | None = None
    locked_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class UserListResponse(AppBaseModel):
    items: list[UserResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
