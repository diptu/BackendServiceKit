"""Pydantic schemas for Session endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class CreateSessionRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID
    header, same convention as every other service in this repo."""

    user_id: UUID
    device_info: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=512)
    ttl_seconds: int | None = Field(default=None, ge=1)


class SessionResponse(AppBaseModel):
    id: UUID
    user_id: UUID
    status: str
    device_info: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class CreateSessionResponse(AppBaseModel):
    """The raw session token is returned exactly once, here."""

    session_token: str
    session: SessionResponse


class SessionListResponse(AppBaseModel):
    items: list[SessionResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False


class RevokeAllRequest(AppBaseModel):
    user_id: UUID


class RevokeAllResponse(AppBaseModel):
    revoked: int
