"""TenantLifecycleService — business logic for lifecycle state transitions."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    VALID_TRANSITIONS,
    TenantLifecycleStatus,
    TransitionType,
)
from app.domain.events import (
    TenantActivated,
    TenantArchived,
    TenantDeleted,
    TenantLocked,
    TenantReactivated,
    TenantSuspended,
)
from app.domain.exceptions import (
    InvalidLifecycleTransitionError,
    TenantLifecycleNotFoundError,
)
from app.infrastructure.clients.tenant_management import TenantManagementClient
from app.models.tenant_lifecycle_event import TenantLifecycleEvent
from app.models.tenant_lifecycle_state import TenantLifecycleState
from app.repositories.base import PageResult
from app.repositories.lifecycle_event import LifecycleEventRepository
from app.repositories.lifecycle_state import LifecycleStateRepository

logger = logging.getLogger(__name__)


def _emit(event: Any) -> None:
    """Log a domain event. Replace with a message broker publisher in production."""
    logger.debug(
        "domain_event",
        extra={"event_type": type(event).__name__, **asdict(event)},
    )


class TenantLifecycleService:
    """Orchestrates all lifecycle transitions and history queries."""

    __slots__ = ("_state_repo", "_event_repo", "_tm_client")

    def __init__(self, session: AsyncSession) -> None:
        self._state_repo = LifecycleStateRepository(session)
        self._event_repo = LifecycleEventRepository(session)
        self._tm_client = TenantManagementClient()

    # ------------------------------------------------------------------
    # Public transition methods
    # ------------------------------------------------------------------

    async def activate(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition PROVISIONING → ACTIVE (first activation).

        Auto-creates a PROVISIONING record if none exists, so callers can
        activate a tenant not yet registered with the Lifecycle Service.
        Idempotent: returns the current state without error when already ACTIVE.
        Matches PUT semantics — safe to retry.
        """
        state = await self._state_repo.get_by_tenant_id(tenant_id)
        if state is None:
            state = await self._state_repo.create(
                TenantLifecycleState(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    current_status=TenantLifecycleStatus.PROVISIONING.value,
                    previous_status=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )

        if TenantLifecycleStatus(state.current_status) == TenantLifecycleStatus.ACTIVE:
            return state

        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.ACTIVE,
            transition=TransitionType.ACTIVATE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantActivated(tenant_id=tenant_id, activated_by=performed_by))
        await self._tm_client.sync_transition(tenant_id, TransitionType.ACTIVATE, reason=reason)
        return state

    async def suspend_idempotent(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition ACTIVE → SUSPENDED (idempotent PUT variant).

        Returns the current state without error when already SUSPENDED.
        Raises 409 for all other source states.
        """
        state = await self._get_or_404(tenant_id)
        if TenantLifecycleStatus(state.current_status) == TenantLifecycleStatus.SUSPENDED:
            return state
        return await self.suspend(
            tenant_id, reason=reason, performed_by=performed_by, source=source
        )

    async def suspend(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition ACTIVE → SUSPENDED."""
        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.SUSPENDED,
            transition=TransitionType.SUSPEND,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantSuspended(tenant_id=tenant_id, suspended_by=performed_by, reason=reason))
        await self._tm_client.sync_transition(tenant_id, TransitionType.SUSPEND, reason=reason)
        return state

    async def reactivate(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition SUSPENDED → ACTIVE."""
        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.ACTIVE,
            transition=TransitionType.REACTIVATE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantReactivated(tenant_id=tenant_id, reactivated_by=performed_by))
        await self._tm_client.sync_transition(tenant_id, TransitionType.REACTIVATE, reason=reason)
        return state

    async def lock(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition ACTIVE → LOCKED."""
        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.LOCKED,
            transition=TransitionType.LOCK,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantLocked(tenant_id=tenant_id, locked_by=performed_by, reason=reason))
        # TenantManagement has no "locked" state; suspend is the closest proxy.
        await self._tm_client.sync_transition(tenant_id, TransitionType.LOCK, reason=reason)
        return state

    async def archive(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition ACTIVE | SUSPENDED | LOCKED → ARCHIVED."""
        existing = await self._get_or_404(tenant_id)
        previous = TenantLifecycleStatus(existing.current_status)

        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.ARCHIVED,
            transition=TransitionType.ARCHIVE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(
            TenantArchived(
                tenant_id=tenant_id,
                archived_by=performed_by,
                previous_status=previous.value,
                reason=reason,
            )
        )
        await self._tm_client.sync_transition(tenant_id, TransitionType.ARCHIVE, reason=reason)
        return state

    async def delete(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition ARCHIVED → DELETED."""
        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.DELETED,
            transition=TransitionType.DELETE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantDeleted(tenant_id=tenant_id, deleted_by=performed_by, reason=reason))
        await self._tm_client.sync_transition(tenant_id, TransitionType.DELETE, reason=reason)
        return state

    async def get_history(
        self,
        tenant_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> PageResult[TenantLifecycleEvent]:
        """Return the paginated event history for a tenant."""
        if not await self._state_repo.exists_by_tenant_id(tenant_id):
            raise TenantLifecycleNotFoundError(tenant_id)
        return await self._event_repo.list_by_tenant_id(
            tenant_id, limit=limit, offset=offset
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_or_404(self, tenant_id: UUID) -> TenantLifecycleState:
        state = await self._state_repo.get_by_tenant_id(tenant_id)
        if state is None:
            raise TenantLifecycleNotFoundError(tenant_id)
        return state

    async def _transition(
        self,
        tenant_id: UUID,
        *,
        target: TenantLifecycleStatus,
        transition: TransitionType,
        reason: str | None,
        performed_by: UUID | None,
        source: str,
    ) -> TenantLifecycleState:
        state = await self._get_or_404(tenant_id)
        current = TenantLifecycleStatus(state.current_status)

        if target not in VALID_TRANSITIONS.get(current, frozenset()):
            raise InvalidLifecycleTransitionError(current, target)

        previous = current
        state.previous_status = previous.value
        state.current_status = target.value
        state.updated_at = datetime.now(timezone.utc)
        state = await self._state_repo.save(state)

        await self._event_repo.append(
            TenantLifecycleEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                from_status=previous.value,
                to_status=target.value,
                transition=transition.value,
                reason=reason,
                performed_by=performed_by,
                source=source,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        return state
