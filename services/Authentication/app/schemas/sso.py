"""Pydantic schemas for SSO (OIDC) endpoints."""

from __future__ import annotations

from app.schemas.base import AppBaseModel


class SsoLoginResponse(AppBaseModel):
    """The IdP authorization URL the client must redirect the user to."""

    authorization_url: str


class SsoCallbackRequest(AppBaseModel):
    code: str
    state: str


class SsoTokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
