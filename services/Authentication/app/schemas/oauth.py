"""Pydantic schemas for OAuth2.1 endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import AppBaseModel


class RegisterClientRequest(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    redirect_uris: list[str] = Field(..., min_length=1)
    allowed_scopes: list[str] | None = None
    is_confidential: bool = True


class RegisterClientResponse(AppBaseModel):
    """`client_secret` is returned once and only for confidential clients —
    public clients get `null` and must use PKCE instead."""

    client_id: str
    client_secret: str | None = None
    is_confidential: bool


class TokenRequest(AppBaseModel):
    """The `/oauth/token` request body. Supports grant_type=authorization_code
    (code + PKCE code_verifier) and grant_type=refresh_token (refresh_token)."""

    grant_type: str
    code: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    code_verifier: str | None = None
    refresh_token: str | None = None


class OAuthTokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str | None = None
