"""Repositories for the OAuth2.1 aggregate (clients, authorization codes)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

from app.models.authorization_code import AuthorizationCode
from app.models.oauth_client import OAuthClient
from app.repositories.base import BaseRepository


class OAuthClientRepository(BaseRepository[OAuthClient]):
    async def create(self, client: OAuthClient) -> OAuthClient:
        self._session.add(client)
        await self._session.flush()
        return client

    async def get(self, client_id: str) -> OAuthClient | None:
        result = await self._session.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        return result.scalar_one_or_none()


class AuthorizationCodeRepository(BaseRepository[AuthorizationCode]):
    async def create(self, code: AuthorizationCode) -> AuthorizationCode:
        self._session.add(code)
        await self._session.flush()
        return code

    async def get_by_hash(
        self, code_hash: str, *, tenant_id: UUID
    ) -> AuthorizationCode | None:
        result = await self._session.execute(
            select(AuthorizationCode).where(
                AuthorizationCode.code_hash == code_hash,
                AuthorizationCode.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, code_id: UUID, *, tenant_id: UUID) -> None:
        await self._session.execute(
            update(AuthorizationCode)
            .where(
                AuthorizationCode.id == code_id,
                AuthorizationCode.tenant_id == tenant_id,
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
        await self._session.flush()
