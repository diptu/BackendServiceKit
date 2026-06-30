"""TenantContactRepository — ownership and admin contact management."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.tenant_contact import TenantContact
from app.repositories.base import BaseRepository


class TenantContactRepository(BaseRepository[TenantContact]):
    async def get_active_by_tenant(self, tenant_id: UUID) -> list[TenantContact]:
        result = await self._session.execute(
            select(TenantContact)
            .where(TenantContact.tenant_id == tenant_id)
            .where(TenantContact.removed_at.is_(None))
            .order_by(TenantContact.added_at)
        )
        return list(result.scalars())

    async def get_by_id(self, contact_id: UUID) -> TenantContact | None:
        result = await self._session.execute(
            select(TenantContact).where(TenantContact.id == contact_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> TenantContact | None:
        result = await self._session.execute(
            select(TenantContact)
            .where(TenantContact.tenant_id == tenant_id)
            .where(TenantContact.user_id == user_id)
            .where(TenantContact.removed_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def count_active_owners(self, tenant_id: UUID) -> int:
        result = await self._session.scalar(
            select(func.count(TenantContact.id))
            .where(TenantContact.tenant_id == tenant_id)
            .where(TenantContact.role == "owner")
            .where(TenantContact.removed_at.is_(None))
        )
        return result or 0

    async def create(self, contact: TenantContact) -> TenantContact:
        self._session.add(contact)
        await self._session.flush()
        await self._session.refresh(contact)
        return contact

    async def remove(self, contact: TenantContact) -> None:
        from datetime import datetime, timezone

        contact.removed_at = datetime.now(timezone.utc)
        self._session.add(contact)
        await self._session.flush()
