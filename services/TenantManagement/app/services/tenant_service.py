"""TenantService — business logic for the Tenant aggregate root."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TenantStatus, VALID_TRANSITIONS
from app.domain.events import (
    TenantActivated,
    TenantArchived,
    TenantCreated,
    TenantDeleted,
    TenantReactivated,
    TenantSuspended,
    TenantUpdated,
)
from app.domain.exceptions import (
    InvalidTenantTransitionError,
    TenantLockedError,
    TenantNameConflictError,
    TenantNotFoundError,
)
from app.models.tenant import Tenant
from app.models.tenant_contact import TenantContact
from app.models.tenant_settings import TenantSettings
from app.repositories.base import PageResult
from app.repositories.tenant import TenantFilter, TenantRepository
from app.repositories.tenant_contact import TenantContactRepository
from app.repositories.tenant_settings import TenantSettingsRepository
from app.schemas.tenant import CreateTenantRequest, UpdateTenantRequest

logger = logging.getLogger(__name__)

# Placeholder caller UUID used until auth middleware provides a real identity.
_SYSTEM_ACTOR = UUID("00000000-0000-0000-0000-000000000000")


def _emit(event: Any) -> None:
    """Log a domain event. Replaced by a message broker in production."""
    logger.debug("domain_event", extra={"event_type": type(event).__name__, **asdict(event)})


class TenantService:
    """Orchestrates all business logic for tenant creation, retrieval, update,
    lifecycle transitions, and soft-deletion."""

    __slots__ = ("_repo", "_settings_repo", "_contact_repo")

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TenantRepository(session)
        self._settings_repo = TenantSettingsRepository(session)
        self._contact_repo = TenantContactRepository(session)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, request: CreateTenantRequest) -> Tenant:
        """Atomically provision a new tenant with its default settings and initial owner.

        Three rows are written in a single transaction:
        1. ``Tenant``        — master record, starts in ``draft`` state.
        2. ``TenantSettings``— seeded from the request's timezone/locale/currency.
        3. ``TenantContact`` — the ``owner_id`` as the first ``owner``-role contact.

        Raises:
            TenantNameConflictError: if the slug is already taken (including
                soft-deleted tenants, whose slugs remain reserved).
        """
        if await self._repo.exists_by_name(request.name):
            raise TenantNameConflictError(request.name)

        now = datetime.now(timezone.utc)
        tenant_id = uuid4()

        # 1 — Tenant row
        tenant = Tenant(
            id=tenant_id,
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            status=TenantStatus.DRAFT,
            region=request.region,
            timezone=request.timezone,
            locale=request.locale,
            currency=request.currency,
            owner_id=request.owner_id,
            created_at=now,
            updated_at=now,
        )
        tenant = await self._repo.create(tenant)

        # 2 — Default TenantSettings (seeded from request values so the
        #     settings row reflects the same timezone/locale/currency as the
        #     tenant record without a separate PATCH call).
        await self._settings_repo.create(
            TenantSettings(
                id=uuid4(),
                tenant_id=tenant_id,
                timezone=request.timezone,
                locale=request.locale,
                currency=request.currency,
            )
        )

        # 3 — Initial owner contact (owner_id becomes the first active owner)
        await self._contact_repo.create(
            TenantContact(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=request.owner_id,
                role="owner",
                added_at=now,
            )
        )

        _emit(
            TenantCreated(
                tenant_id=tenant.id,
                name=tenant.name,
                region=tenant.region,
                owner_id=tenant.owner_id,
            )
        )
        return tenant

    async def get(self, tenant_id: UUID) -> Tenant:
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        return tenant

    async def list(
        self,
        *,
        status_filter: TenantStatus | str | None = None,
        region: str | None = None,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Tenant]:
        filters: TenantFilter | None = None
        if status_filter is not None or region is not None or search is not None:
            # Accept both TenantStatus enum values and raw strings so the
            # service can be called directly in tests without wrapping strings.
            status = TenantStatus(status_filter) if status_filter is not None else None
            filters = TenantFilter(status=status, region=region, search=search)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def update(self, tenant_id: UUID, request: UpdateTenantRequest) -> Tenant:
        tenant = await self._require_writable(tenant_id)

        changed: list[str] = []
        for field_name in ("display_name", "description", "region", "timezone", "locale", "currency"):
            new_val = getattr(request, field_name)
            if new_val is not None and getattr(tenant, field_name) != new_val:
                setattr(tenant, field_name, new_val)
                changed.append(field_name)

        if changed:
            tenant.updated_at = datetime.now(timezone.utc)
            tenant = await self._repo.save(tenant)
            _emit(
                TenantUpdated(
                    tenant_id=tenant.id,
                    updated_by=_SYSTEM_ACTOR,
                    changed_fields=changed,
                )
            )
        return tenant

    async def delete(self, tenant_id: UUID) -> None:
        tenant = await self.get(tenant_id)
        current = TenantStatus(tenant.status)
        if current != TenantStatus.ARCHIVED:
            raise InvalidTenantTransitionError(current, TenantStatus.DELETED)
        await self._repo.soft_delete(tenant)
        _emit(TenantDeleted(tenant_id=tenant.id, deleted_by=_SYSTEM_ACTOR))

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    async def activate(self, tenant_id: UUID, reason: str | None = None) -> Tenant:
        tenant = await self.get(tenant_id)
        current = TenantStatus(tenant.status)
        self._check_transition(current, TenantStatus.ACTIVE)

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.now(timezone.utc)
        tenant = await self._repo.save(tenant)

        if current == TenantStatus.SUSPENDED:
            _emit(TenantReactivated(tenant_id=tenant.id, reactivated_by=_SYSTEM_ACTOR))
        else:
            _emit(TenantActivated(tenant_id=tenant.id, activated_by=_SYSTEM_ACTOR))
        return tenant

    async def suspend(self, tenant_id: UUID, reason: str | None = None) -> Tenant:
        tenant = await self.get(tenant_id)
        current = TenantStatus(tenant.status)
        self._check_transition(current, TenantStatus.SUSPENDED)

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.now(timezone.utc)
        tenant = await self._repo.save(tenant)
        _emit(TenantSuspended(tenant_id=tenant.id, suspended_by=_SYSTEM_ACTOR, reason=reason))
        return tenant

    async def archive(self, tenant_id: UUID, reason: str | None = None) -> Tenant:
        tenant = await self.get(tenant_id)
        current = TenantStatus(tenant.status)
        self._check_transition(current, TenantStatus.ARCHIVED)

        previous = current
        tenant.status = TenantStatus.ARCHIVED
        tenant.updated_at = datetime.now(timezone.utc)
        tenant = await self._repo.save(tenant)
        _emit(
            TenantArchived(
                tenant_id=tenant.id,
                archived_by=_SYSTEM_ACTOR,
                previous_status=previous,
            )
        )
        return tenant

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _require_writable(self, tenant_id: UUID) -> Tenant:
        """Load a tenant and raise TenantLockedError if it is archived."""
        tenant = await self.get(tenant_id)
        if TenantStatus(tenant.status) == TenantStatus.ARCHIVED:
            raise TenantLockedError(tenant_id)
        return tenant

    @staticmethod
    def _check_transition(current: TenantStatus, target: TenantStatus) -> None:
        if target not in VALID_TRANSITIONS.get(current, frozenset()):
            raise InvalidTenantTransitionError(current, target)
