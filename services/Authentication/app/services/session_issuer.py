"""Shared access + refresh token-pair issuance.

Password login (AuthService), the OAuth2.1 token endpoint (OAuthService) and
the SSO callback (SsoService) all mint sessions through this one function so
every issued session is the same shape and equally revocable — there is no
second, weaker way to get tokens out of this service.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token import RefreshTokenRepository
from app.services.token_service import create_access_token, generate_opaque_token


class AuthTokenPair:
    __slots__ = ("access_token", "refresh_token")

    def __init__(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token


async def issue_token_pair(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    scopes: list[str] | None = None,
    device_info: str | None = None,
) -> AuthTokenPair:
    access_token = create_access_token(tenant_id, user_id, scopes)
    raw_refresh, refresh_hash = generate_opaque_token()
    now = datetime.now(timezone.utc)
    await RefreshTokenRepository(session).create(
        RefreshToken(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            token_hash=refresh_hash,
            device_info=device_info,
            issued_at=now,
            expires_at=now + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
    )
    return AuthTokenPair(access_token=access_token, refresh_token=raw_refresh)
