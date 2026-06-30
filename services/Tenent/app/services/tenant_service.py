"""TenantService — authoritative CRUD and lifecycle transitions for Tenant."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import (
    AddOwnerCmd,
    CreateTenantCmd,
    UpdateTenantMetadataCmd,
    UpdateTenantCmd,
    UpdateTenantSettingsCmd,
)
from app.domain.enums import OwnerRole, TenantStatus, VALID_TRANSITIONS
from app.domain.exceptions import (
    InvalidTenantTransitionError,
    TenantContactConflictError,
    TenantContactNotFoundError,
    TenantDeletedError,
    TenantNameConflictError,
    TenantNotFoundError,
    TenantOwnerRequiredError,
)
from app.models.tenant import Tenant
from app.models.tenant_contact import TenantContact
from app.models.tenant_metadata import TenantMetadata
from app.models.tenant_settings import TenantSettings
from app.repositories.tenant import TenantFilter, TenantRepository
from app.repositories.tenant_contact import TenantContactRepository
from app.repositories.tenant_metadata import TenantMetadataRepository
from app.repositories.tenant_settings import TenantSettingsRepository

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tenant_repo = TenantRepository(session)
        self._contact_repo = TenantContactRepository(session)
        self._settings_repo = TenantSettingsRepository(session)
        self._metadata_repo = TenantMetadataRepository(session)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, cmd: CreateTenantCmd) -> Tenant:
        if await self._tenant_repo.exists_by_name(cmd.name):
            raise TenantNameConflictError(cmd.name)

        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name=cmd.name,
            display_name=cmd.display_name,
            description=cmd.description,
            status=TenantStatus.DRAFT,
            region=cmd.region,
            timezone=cmd.timezone,
            locale=cmd.locale,
            currency=cmd.currency,
            owner_id=cmd.owner_id,
        )
        await self._tenant_repo.create(tenant)

        settings = TenantSettings(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            timezone=cmd.timezone,
            locale=cmd.locale,
            currency=cmd.currency,
        )
        await self._settings_repo.create(settings)

        contact = TenantContact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=cmd.owner_id,
            role=OwnerRole.OWNER,
        )
        await self._contact_repo.create(contact)

        return tenant

    async def get(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        return tenant

    async def list(
        self,
        *,
        filters: TenantFilter | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> object:
        return await self._tenant_repo.list(filters=filters, cursor=cursor, limit=limit)

    async def update(self, tenant_id: uuid.UUID, cmd: UpdateTenantCmd) -> Tenant:
        tenant = await self.get(tenant_id)
        if tenant.deleted_at is not None:
            raise TenantDeletedError(tenant_id)

        if cmd.display_name is not None:
            tenant.display_name = cmd.display_name
        if cmd.description is not None:
            tenant.description = cmd.description
        if cmd.timezone is not None:
            tenant.timezone = cmd.timezone
        if cmd.locale is not None:
            tenant.locale = cmd.locale
        if cmd.currency is not None:
            tenant.currency = cmd.currency

        return await self._tenant_repo.save(tenant)

    async def delete(self, tenant_id: uuid.UUID) -> None:
        tenant = await self.get(tenant_id)
        if tenant.deleted_at is not None:
            return
        self._assert_transition(tenant, TenantStatus.DELETED)
        await self._tenant_repo.soft_delete(tenant)

    # ------------------------------------------------------------------
    # Lifecycle transitions (called by TenantLifecycleService internally)
    # ------------------------------------------------------------------

    async def provision(self, tenant_id: uuid.UUID) -> Tenant:
        return await self._transition(tenant_id, TenantStatus.PROVISIONING)

    async def pend(self, tenant_id: uuid.UUID) -> Tenant:
        return await self._transition(tenant_id, TenantStatus.PENDING)

    async def activate(self, tenant_id: uuid.UUID) -> Tenant:
        return await self._transition(tenant_id, TenantStatus.ACTIVE)

    async def suspend(self, tenant_id: uuid.UUID) -> Tenant:
        return await self._transition(tenant_id, TenantStatus.SUSPENDED)

    async def archive(self, tenant_id: uuid.UUID) -> Tenant:
        return await self._transition(tenant_id, TenantStatus.ARCHIVED)

    # ------------------------------------------------------------------
    # Settings sub-resource
    # ------------------------------------------------------------------

    async def get_settings(self, tenant_id: uuid.UUID) -> TenantSettings | None:
        return await self._settings_repo.get_by_tenant_id(tenant_id)

    async def update_settings(
        self, tenant_id: uuid.UUID, cmd: UpdateTenantSettingsCmd
    ) -> TenantSettings:
        settings = await self._settings_repo.get_by_tenant_id(tenant_id)
        if settings is None:
            settings = TenantSettings(id=uuid.uuid4(), tenant_id=tenant_id)

        for field_name, value in cmd.__dict__.items():
            if value is not None:
                setattr(settings, field_name, value)

        return await self._settings_repo.save(settings)

    # ------------------------------------------------------------------
    # Owners / contacts sub-resource
    # ------------------------------------------------------------------

    async def list_owners(self, tenant_id: uuid.UUID) -> list[TenantContact]:
        await self.get(tenant_id)
        return await self._contact_repo.get_active_by_tenant(tenant_id)

    async def add_owner(self, tenant_id: uuid.UUID, cmd: AddOwnerCmd) -> TenantContact:
        await self.get(tenant_id)
        existing = await self._contact_repo.get_active_by_user(tenant_id, cmd.user_id)
        if existing is not None:
            raise TenantContactConflictError(tenant_id, cmd.user_id)

        contact = TenantContact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=cmd.user_id,
            role=cmd.role,
        )
        return await self._contact_repo.create(contact)

    async def remove_owner(
        self, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> None:
        contact = await self._contact_repo.get_by_id(contact_id)
        if contact is None or contact.tenant_id != tenant_id:
            raise TenantContactNotFoundError(contact_id)
        if contact.removed_at is not None:
            return

        if contact.role == OwnerRole.OWNER:
            active_owners = await self._contact_repo.count_active_owners(tenant_id)
            if active_owners <= 1:
                raise TenantOwnerRequiredError(tenant_id)

        await self._contact_repo.remove(contact)

    # ------------------------------------------------------------------
    # Metadata sub-resource
    # ------------------------------------------------------------------

    async def get_metadata(self, tenant_id: uuid.UUID) -> list[TenantMetadata]:
        await self.get(tenant_id)
        return await self._metadata_repo.get_all_for_tenant(tenant_id)

    async def update_metadata(
        self, tenant_id: uuid.UUID, cmd: UpdateTenantMetadataCmd
    ) -> list[TenantMetadata]:
        await self.get(tenant_id)
        return await self._metadata_repo.upsert_many(tenant_id, cmd.metadata)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _assert_transition(self, tenant: Tenant, target: TenantStatus) -> None:
        current = TenantStatus(tenant.status)
        if target not in VALID_TRANSITIONS.get(current, frozenset()):
            raise InvalidTenantTransitionError(current, target)

    async def _transition(self, tenant_id: uuid.UUID, target: TenantStatus) -> Tenant:
        tenant = await self.get(tenant_id)
        self._assert_transition(tenant, target)
        tenant.status = target
        return await self._tenant_repo.save(tenant)
