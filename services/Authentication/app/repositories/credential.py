"""Repository for Credential.

tenant_id is a required keyword argument on every lookup — not optional —
per this session's own hardening of the same pattern in IAM's repositories
(services/IAM/app/repositories/*.py): an optional tenant_id is a one-line
mistake away from a cross-tenant credential lookup.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.credential import Credential
from app.repositories.base import BaseRepository


class CredentialRepository(BaseRepository[Credential]):
    async def create(self, credential: Credential) -> Credential:
        self._session.add(credential)
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    async def save(self, credential: Credential) -> Credential:
        self._session.add(credential)
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    async def get_by_user_id(
        self, user_id: UUID, *, tenant_id: UUID
    ) -> Credential | None:
        result = await self._session.execute(
            select(Credential).where(
                Credential.user_id == user_id, Credential.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, *, tenant_id: UUID) -> Credential | None:
        result = await self._session.execute(
            select(Credential).where(
                Credential.email == email, Credential.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str, *, tenant_id: UUID) -> bool:
        return await self.get_by_email(email, tenant_id=tenant_id) is not None
