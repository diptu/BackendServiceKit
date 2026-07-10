"""Repositories for the SSO/OIDC aggregate (states, federated identities)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

from app.models.sso_identity import SsoIdentity
from app.models.sso_state import SsoState
from app.repositories.base import BaseRepository


class SsoStateRepository(BaseRepository[SsoState]):
    async def create(self, state: SsoState) -> SsoState:
        self._session.add(state)
        await self._session.flush()
        return state

    async def get(self, state: str, *, tenant_id: UUID) -> SsoState | None:
        result = await self._session.execute(
            select(SsoState).where(
                SsoState.state == state, SsoState.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, state: str, *, tenant_id: UUID) -> None:
        await self._session.execute(
            update(SsoState)
            .where(SsoState.state == state, SsoState.tenant_id == tenant_id)
            .values(consumed_at=datetime.now(timezone.utc))
        )
        await self._session.flush()


class SsoIdentityRepository(BaseRepository[SsoIdentity]):
    async def create(self, identity: SsoIdentity) -> SsoIdentity:
        self._session.add(identity)
        await self._session.flush()
        return identity

    async def get_by_subject(
        self, provider: str, subject: str, *, tenant_id: UUID
    ) -> SsoIdentity | None:
        result = await self._session.execute(
            select(SsoIdentity).where(
                SsoIdentity.provider == provider,
                SsoIdentity.subject == subject,
                SsoIdentity.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def touch_login(self, identity: SsoIdentity) -> None:
        identity.last_login_at = datetime.now(timezone.utc)
        await self._session.flush()
