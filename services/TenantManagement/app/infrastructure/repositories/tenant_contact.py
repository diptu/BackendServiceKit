"""TenantContactRepository — ownership and admin contact management."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.infrastructure.database.models.tenant_contact import TenantContact
from app.infrastructure.repositories.base import BaseRepository


class TenantContactRepository(BaseRepository[TenantContact]):
    """Database operations for TenantContact (tenant owners and admins).

    An "active" contact is one where ``removed_at IS NULL``.
    Every tenant must retain at least one active owner at all times — this
    invariant is enforced at the service layer, not here.
    """

    async def get_active_by_tenant(self, tenant_id: UUID) -> list[TenantContact]:
        """Return all active (not removed) contacts for a tenant."""
        result = await self._session.execute(
            select(TenantContact)
            .where(TenantContact.tenant_id == tenant_id)
            .where(TenantContact.removed_at.is_(None))
            .order_by(TenantContact.added_at)
        )
        return list(result.scalars())

    async def get_by_id(self, contact_id: UUID) -> TenantContact | None:
        """Return a contact by primary key, or ``None``."""
        result = await self._session.execute(
            select(TenantContact).where(TenantContact.id == contact_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> TenantContact | None:
        """Return the active contact for a specific user on a tenant, or ``None``."""
        result = await self._session.execute(
            select(TenantContact)
            .where(TenantContact.tenant_id == tenant_id)
            .where(TenantContact.user_id == user_id)
            .where(TenantContact.removed_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def count_active_owners(self, tenant_id: UUID) -> int:
        """Return the number of active owner-role contacts for a tenant.

        Used to enforce the "at least one owner" invariant before removal.
        """
        result = await self._session.scalar(
            select(func.count(TenantContact.id))
            .where(TenantContact.tenant_id == tenant_id)
            .where(TenantContact.role == "owner")
            .where(TenantContact.removed_at.is_(None))
        )
        return result or 0

    async def create(self, contact: TenantContact) -> TenantContact:
        """Persist a new contact and return it with server defaults."""
        self._session.add(contact)
        await self._session.flush()
        await self._session.refresh(contact)
        return contact

    async def remove(self, contact: TenantContact) -> None:
        """Soft-remove a contact by setting ``removed_at`` to now.

        The row is retained for audit purposes.
        """
        from datetime import datetime, timezone

        contact.removed_at = datetime.now(timezone.utc)
        self._session.add(contact)
        await self._session.flush()
