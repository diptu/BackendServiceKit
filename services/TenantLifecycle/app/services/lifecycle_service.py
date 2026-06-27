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
    TenantPended,
    TenantProvisioningStarted,
    TenantReactivated,
    TenantSuspended,
    TenantUnlocked,
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

    async def provision(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Register a tenant with TL and start provisioning (DRAFT → PROVISIONING in TM).

        Idempotent: returns the current state without error if already PROVISIONING.
        Raises 409 for all other existing states.

        Calls TM's POST /provision to advance TM from draft → provisioning.
        """
        state = await self._state_repo.get_by_tenant_id(tenant_id)

        if state is not None:
            if TenantLifecycleStatus(state.current_status) == TenantLifecycleStatus.PROVISIONING:
                return state  # idempotent
            raise InvalidLifecycleTransitionError(
                TenantLifecycleStatus(state.current_status),
                TenantLifecycleStatus.PROVISIONING,
            )

        now = datetime.now(timezone.utc)
        state = await self._state_repo.create(
            TenantLifecycleState(
                id=uuid4(),
                tenant_id=tenant_id,
                current_status=TenantLifecycleStatus.PROVISIONING.value,
                previous_status=None,
                created_at=now,
                updated_at=now,
            )
        )
        await self._event_repo.append(
            TenantLifecycleEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                from_status=None,
                to_status=TenantLifecycleStatus.PROVISIONING.value,
                transition=TransitionType.PROVISION.value,
                reason=reason,
                performed_by=performed_by,
                source=source,
                occurred_at=now,
            )
        )
        _emit(TenantProvisioningStarted(
            tenant_id=tenant_id, provisioned_by=performed_by, reason=reason
        ))
        await self._tm_client.sync_transition(tenant_id, TransitionType.PROVISION, reason=reason)
        return state

    async def pend(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition PROVISIONING → PENDING (pre-activation compliance gate).

        Idempotent: returns the current state without error when already PENDING.
        Matches PUT semantics — safe to retry.

        TM is intentionally NOT synced for this transition: TM has no pending state,
        so it stays in provisioning until activate() calls TM's POST /activate.
        """
        state = await self._get_or_404(tenant_id)

        if TenantLifecycleStatus(state.current_status) == TenantLifecycleStatus.PENDING:
            return state  # idempotent

        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.PENDING,
            transition=TransitionType.PEND,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantPended(tenant_id=tenant_id, pended_by=performed_by, reason=reason))
        # No TM sync: TM has no pending state; TM remains in provisioning until activate().
        return state

    async def activate(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition PENDING → ACTIVE.

        Idempotent: returns the current state without error when already ACTIVE.
        Matches PUT semantics — safe to retry.
        Callers must call pend() first to move through PROVISIONING → PENDING.
        """
        state = await self._get_or_404(tenant_id)
        current = TenantLifecycleStatus(state.current_status)

        if current == TenantLifecycleStatus.ACTIVE:
            return state  # idempotent

        # activate() is specifically PENDING → ACTIVE.
        # SUSPENDED → ACTIVE uses reactivate(); LOCKED → ACTIVE uses unlock().
        if current != TenantLifecycleStatus.PENDING:
            raise InvalidLifecycleTransitionError(current, TenantLifecycleStatus.ACTIVE)

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
        Bootstraps a TL record from TM's authoritative state when none exists yet.
        """
        state = await self._state_repo.get_by_tenant_id(tenant_id)
        if state is None:
            state = await self._bootstrap_from_tm(tenant_id)
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
        """Transition SUSPENDED → ACTIVE.

        Only valid from SUSPENDED. Use unlock() for LOCKED → ACTIVE.
        """
        current_state = await self._get_or_404(tenant_id)
        if TenantLifecycleStatus(current_state.current_status) != TenantLifecycleStatus.SUSPENDED:
            raise InvalidLifecycleTransitionError(
                TenantLifecycleStatus(current_state.current_status),
                TenantLifecycleStatus.ACTIVE,
            )
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

    async def unlock(
        self,
        tenant_id: UUID,
        *,
        reason: str | None = None,
        performed_by: UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Transition LOCKED → ACTIVE (security incident resolved).

        Called by an admin after investigation confirms the tenant is safe to resume.
        Syncs TM from suspended → active (TM has no locked state; lock proxied as suspend).
        Only valid from LOCKED — use reactivate() for SUSPENDED → ACTIVE.
        """
        current_state = await self._get_or_404(tenant_id)
        if TenantLifecycleStatus(current_state.current_status) != TenantLifecycleStatus.LOCKED:
            raise InvalidLifecycleTransitionError(
                TenantLifecycleStatus(current_state.current_status),
                TenantLifecycleStatus.ACTIVE,
            )
        state = await self._transition(
            tenant_id,
            target=TenantLifecycleStatus.ACTIVE,
            transition=TransitionType.UNLOCK,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        _emit(TenantUnlocked(tenant_id=tenant_id, unlocked_by=performed_by, reason=reason))
        await self._tm_client.sync_transition(tenant_id, TransitionType.UNLOCK, reason=reason)
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
        next_cursor: str | None = None,
    ) -> PageResult[TenantLifecycleEvent]:
        """Return the cursor-paginated event history for a tenant."""
        if not await self._state_repo.exists_by_tenant_id(tenant_id):
            raise TenantLifecycleNotFoundError(tenant_id)
        return await self._event_repo.list_by_tenant_id(
            tenant_id, limit=limit, next_cursor=next_cursor
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _bootstrap_from_tm(self, tenant_id: UUID) -> TenantLifecycleState:
        """Create a TL record seeded from TM's current authoritative state.

        Used when a tenant was provisioned before TL was deployed or before the
        first pend() call. Queries TM for the current status and seeds TL with it.
        Raises TenantLifecycleNotFoundError if TM also has no record.
        """
        tm_status = await self._tm_client.get_status(tenant_id)
        if tm_status is None:
            raise TenantLifecycleNotFoundError(tenant_id)

        try:
            tl_status = TenantLifecycleStatus(tm_status)
        except ValueError:
            # TM has a state TL doesn't recognise (e.g. "draft") — seed as PROVISIONING.
            tl_status = TenantLifecycleStatus.PROVISIONING

        logger.info(
            "Bootstrapping TL record from TenantManagement state",
            extra={"tenant_id": str(tenant_id), "seeded_status": tl_status.value},
        )
        return await self._state_repo.create(
            TenantLifecycleState(
                id=uuid4(),
                tenant_id=tenant_id,
                current_status=tl_status.value,
                previous_status=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

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
