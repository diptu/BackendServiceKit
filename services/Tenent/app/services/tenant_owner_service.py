"""TenantOwnerService — ownership / contact management."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import AddOwnerCmd
from app.domain.exceptions import (
    TenantContactConflictError,
    TenantContactNotFoundError,
    TenantOwnerRequiredError,
)
from app.models.tenant_contact import TenantContact
from app.repositories.tenant_contact import TenantContactRepository


class TenantOwnerService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = TenantContactRepository(session)

    async def list(self, tenant_id: uuid.UUID) -> list[TenantContact]:
        return await self._repo.get_active_by_tenant(tenant_id)

    async def add(self, tenant_id: uuid.UUID, cmd: AddOwnerCmd) -> TenantContact:
        if await self._repo.get_active_by_user(tenant_id, cmd.user_id) is not None:
            raise TenantContactConflictError(tenant_id, cmd.user_id)

        contact = TenantContact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=cmd.user_id,
            role=cmd.role,
        )
        return await self._repo.create(contact)

    async def remove(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> None:
        contact = await self._repo.get_by_id(contact_id)
        if contact is None or contact.tenant_id != tenant_id:
            raise TenantContactNotFoundError(contact_id)
        if contact.removed_at is not None:
            return

        if contact.role == "owner":
            if await self._repo.count_active_owners(tenant_id) <= 1:
                raise TenantOwnerRequiredError(tenant_id)

        await self._repo.remove(contact)
