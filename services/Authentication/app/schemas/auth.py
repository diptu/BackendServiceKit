"""Pydantic schemas for Authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class SetCredentialRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID
    header, same convention as every other service in this repo."""

    user_id: UUID
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)


class LoginRequest(AppBaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class TokenPairResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(AppBaseModel):
    """Login returns one of two shapes. Normally a full token pair. When the
    account has MFA enabled, `mfa_required` is true and only `mfa_token` is
    populated — the client must complete /auth/mfa/verify to get tokens."""

    mfa_required: bool = False
    mfa_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


class RefreshRequest(AppBaseModel):
    refresh_token: str


class RevokeRequest(AppBaseModel):
    refresh_token: str


class IntrospectRequest(AppBaseModel):
    token: str


class IntrospectResponse(AppBaseModel):
    active: bool
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    scopes: list[str] = Field(default_factory=list)


class ChangePasswordRequest(AppBaseModel):
    old_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=8, max_length=255)


class ForgotPasswordRequest(AppBaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ForgotPasswordResponse(AppBaseModel):
    """Always the same shape regardless of whether the email is registered
    — see AuthService.request_password_reset's docstring on enumeration."""

    detail: str = "If that email is registered, a reset link has been sent."
    reset_token: str | None = Field(
        default=None,
        description=(
            "Present only outside production, where no NotificationService "
            "exists yet to deliver it out-of-band. Never populated in "
            "production — see TODO.md."
        ),
    )


class ResetPasswordRequest(AppBaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=255)


class SessionResponse(AppBaseModel):
    id: UUID
    device_info: str | None = None
    issued_at: datetime
    expires_at: datetime


class SessionListResponse(AppBaseModel):
    items: list[SessionResponse]


class AuthEventResponse(AppBaseModel):
    id: UUID
    event_type: str
    detail: str | None = None
    occurred_at: datetime


class AuthEventListResponse(AppBaseModel):
    items: list[AuthEventResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
