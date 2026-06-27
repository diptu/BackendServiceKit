"""TenantOwnerService — business logic for tenant contact / ownership management."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events import TenantOwnerAdded, TenantOwnerRemoved
from app.domain.exceptions import (
    TenantContactConflictError,
    TenantContactNotFoundError,
    TenantNotFoundError,
    TenantOwnerRequiredError,
)
from app.models.tenant_contact import TenantContact
from app.repositories.tenant import TenantRepository
from app.repositories.tenant_contact import TenantContactRepository
from app.schemas.tenant import AddOwnerRequest

logger = logging.getLogger(__name__)

_SYSTEM_ACTOR = UUID("00000000-0000-0000-0000-000000000000")


def _emit(event: Any) -> None:
    logger.debug("domain_event", extra={"event_type": type(event).__name__, **asdict(event)})


class TenantOwnerService:
    """Manages the list of owners and admins (contacts) for a tenant.

    Invariant enforced here: every tenant must retain at least one active
    owner-role contact at all times.
    """

    __slots__ = ("_tenant_repo", "_contact_repo")

    def __init__(self, session: AsyncSession) -> None:
        self._tenant_repo = TenantRepository(session)
        self._contact_repo = TenantContactRepository(session)

    async def list_owners(self, tenant_id: UUID) -> list[TenantContact]:
        if not await self._tenant_repo.exists_by_id(tenant_id):
            raise TenantNotFoundError(tenant_id)
        return await self._contact_repo.get_active_by_tenant(tenant_id)

    async def add_owner(
        self, tenant_id: UUID, request: AddOwnerRequest
    ) -> TenantContact:
        if not await self._tenant_repo.exists_by_id(tenant_id):
            raise TenantNotFoundError(tenant_id)

        existing = await self._contact_repo.get_active_by_user(tenant_id, request.user_id)
        if existing is not None:
            raise TenantContactConflictError(tenant_id, request.user_id)

        contact = TenantContact(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=request.user_id,
            role=str(request.role),
            added_at=datetime.now(timezone.utc),
        )
        contact = await self._contact_repo.create(contact)
        _emit(
            TenantOwnerAdded(
                tenant_id=tenant_id,
                user_id=request.user_id,
                role=str(request.role),
                added_by=_SYSTEM_ACTOR,
            )
        )
        return contact

    async def remove_owner(self, tenant_id: UUID, owner_id: UUID) -> None:
        if not await self._tenant_repo.exists_by_id(tenant_id):
            raise TenantNotFoundError(tenant_id)

        contact = await self._contact_repo.get_by_id(owner_id)
        if (
            contact is None
            or contact.tenant_id != tenant_id
            or contact.removed_at is not None
        ):
            raise TenantContactNotFoundError(owner_id)

        if contact.role == "owner":
            active_owners = await self._contact_repo.count_active_owners(tenant_id)
            if active_owners <= 1:
                raise TenantOwnerRequiredError(tenant_id)

        removed_user = contact.user_id
        await self._contact_repo.remove(contact)
        _emit(
            TenantOwnerRemoved(
                tenant_id=tenant_id,
                user_id=removed_user,
                removed_by=_SYSTEM_ACTOR,
            )
        )
