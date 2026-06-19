"""
Pydantic schemas for the Google OAuth2 / OIDC authentication flow.
"""

from __future__ import annotations

from pydantic import BaseModel


class GoogleLoginInitResponse(BaseModel):
    """Returned by GET /auth/google/login."""

    authorization_url: str


class GoogleCallbackError(BaseModel):
    """Body returned when Google redirects back with an error parameter."""

    detail: str
