"""Pydantic schemas for MFA (TOTP) endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import AppBaseModel


class MfaSetupResponse(AppBaseModel):
    """Returned once, at enrollment. `secret`/`otpauth_uri` provision an
    authenticator app; `recovery_codes` are shown a single time and never
    retrievable again."""

    secret: str
    otpauth_uri: str
    recovery_codes: list[str]


class MfaActivateRequest(AppBaseModel):
    code: str = Field(..., min_length=6, max_length=20)


class MfaVerifyRequest(AppBaseModel):
    """Login step-up: redeem the `mfa_token` from a login response together
    with a TOTP code (or a recovery code)."""

    mfa_token: str
    code: str = Field(..., min_length=6, max_length=20)


class MfaVerifyResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MfaDisableRequest(AppBaseModel):
    code: str = Field(..., min_length=6, max_length=20)
