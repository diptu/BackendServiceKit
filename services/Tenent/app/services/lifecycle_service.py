"""TenantLifecycleService — authoritative state machine for the combined service.

Because TM and TL are merged here, every TM-sync call is replaced with a
direct TenantService call instead of HTTP.  All TM syncs are still fire-and-log
(wrapped in try/except, warning on failure) to preserve the original semantics.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    LIFECYCLE_VALID_TRANSITIONS,
    TenantLifecycleStatus,
    TransitionType,
)
from app.domain.exceptions import (
    InvalidLifecycleTransitionError,
    TenantLifecycleAlreadyExistsError,
    TenantLifecycleNotFoundError,
)
from app.models.lifecycle_event import TenantLifecycleEvent
from app.models.lifecycle_state import TenantLifecycleState
from app.repositories.lifecycle_event import LifecycleEventRepository
from app.repositories.lifecycle_state import LifecycleStateRepository
from app.repositories.tenant import TenantRepository
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)


class TenantLifecycleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._state_repo = LifecycleStateRepository(session)
        self._event_repo = LifecycleEventRepository(session)
        self._tenant_repo = TenantRepository(session)
        self._tenant_svc = TenantService(session)

    # ------------------------------------------------------------------
    # Bootstrap — create lifecycle record (called during provisioning)
    # ------------------------------------------------------------------

    async def bootstrap(self, tenant_id: uuid.UUID) -> TenantLifecycleState:
        existing = await self._state_repo.get_by_tenant_id(tenant_id)
        if existing is not None:
            raise TenantLifecycleAlreadyExistsError(tenant_id)

        state = TenantLifecycleState(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            current_status=TenantLifecycleStatus.PROVISIONING,
        )
        return await self._state_repo.create(state)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    async def provision(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Create lifecycle record + advance TM to provisioning."""
        existing = await self._state_repo.get_by_tenant_id(tenant_id)
        if existing is not None:
            raise TenantLifecycleAlreadyExistsError(tenant_id)

        state = TenantLifecycleState(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            current_status=TenantLifecycleStatus.PROVISIONING,
        )
        state = await self._state_repo.create(state)
        await self._record_event(
            tenant_id=tenant_id,
            from_status=None,
            to_status=TenantLifecycleStatus.PROVISIONING,
            transition=TransitionType.PROVISION,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        await self._sync_tm(tenant_id, "provision")
        return state

    async def pend(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        return await self._transition(
            tenant_id,
            TransitionType.PEND,
            TenantLifecycleStatus.PENDING,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def activate(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        return await self._transition(
            tenant_id,
            TransitionType.ACTIVATE,
            TenantLifecycleStatus.ACTIVE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def suspend_idempotent(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        """Suspend but do not raise if already suspended."""
        state = await self._get_state(tenant_id)
        if state.current_status == TenantLifecycleStatus.SUSPENDED:
            return state
        return await self._transition(
            tenant_id,
            TransitionType.SUSPEND,
            TenantLifecycleStatus.SUSPENDED,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def suspend(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        return await self._transition(
            tenant_id,
            TransitionType.SUSPEND,
            TenantLifecycleStatus.SUSPENDED,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def reactivate(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        return await self._transition(
            tenant_id,
            TransitionType.REACTIVATE,
            TenantLifecycleStatus.ACTIVE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def lock(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        state = await self._transition(
            tenant_id,
            TransitionType.LOCK,
            TenantLifecycleStatus.LOCKED,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        await self._sync_tm(tenant_id, "suspend")  # TM proxies locked as suspended
        return state

    async def unlock(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        state = await self._transition(
            tenant_id,
            TransitionType.UNLOCK,
            TenantLifecycleStatus.ACTIVE,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        await self._sync_tm(tenant_id, "activate")
        return state

    async def archive(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        return await self._transition(
            tenant_id,
            TransitionType.ARCHIVE,
            TenantLifecycleStatus.ARCHIVED,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def delete(
        self,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        return await self._transition(
            tenant_id,
            TransitionType.DELETE,
            TenantLifecycleStatus.DELETED,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

    async def get_state(self, tenant_id: uuid.UUID) -> TenantLifecycleState:
        return await self._get_state(tenant_id)

    async def get_history(
        self,
        tenant_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> object:
        return await self._event_repo.list_by_tenant(
            tenant_id, next_cursor=cursor, limit=limit
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_state(self, tenant_id: uuid.UUID) -> TenantLifecycleState:
        state = await self._state_repo.get_by_tenant_id(tenant_id)
        if state is None:
            raise TenantLifecycleNotFoundError(tenant_id)
        return state

    def _assert_transition(
        self,
        state: TenantLifecycleState,
        target: TenantLifecycleStatus,
    ) -> None:
        current = TenantLifecycleStatus(state.current_status)
        if target not in LIFECYCLE_VALID_TRANSITIONS.get(current, frozenset()):
            raise InvalidLifecycleTransitionError(current, target)

    async def _transition(
        self,
        tenant_id: uuid.UUID,
        transition: TransitionType,
        target: TenantLifecycleStatus,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        source: str = "api",
    ) -> TenantLifecycleState:
        state = await self._get_state(tenant_id)
        self._assert_transition(state, target)

        prev = state.current_status
        state.previous_status = prev
        state.current_status = target
        state = await self._state_repo.save(state)

        await self._record_event(
            tenant_id=tenant_id,
            from_status=TenantLifecycleStatus(prev),
            to_status=target,
            transition=transition,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )

        # Sync TM (fire-and-log)
        tm_action = _TL_TO_TM_ACTION.get(transition)
        if tm_action:
            await self._sync_tm(tenant_id, tm_action)

        return state

    async def _sync_tm(self, tenant_id: uuid.UUID, action: str) -> None:
        """Call TenantService directly (no HTTP). Failures are non-fatal.

        For "activate": TM was left in provisioning (PEND skips TM sync),
        so we must pend first, then activate to reach active.
        """
        try:
            if action == "provision":
                await self._tenant_svc.provision(tenant_id)
            elif action == "pend":
                await self._tenant_svc.pend(tenant_id)
            elif action == "activate":
                # TM may be in provisioning state — bridge via pend first
                tm_tenant = await self._tenant_repo.get_by_id(tenant_id)
                if tm_tenant is not None and tm_tenant.status == "provisioning":
                    await self._tenant_svc.pend(tenant_id)
                await self._tenant_svc.activate(tenant_id)
            elif action == "suspend":
                await self._tenant_svc.suspend(tenant_id)
            elif action == "archive":
                await self._tenant_svc.archive(tenant_id)
            elif action == "delete":
                await self._tenant_svc.delete(tenant_id)
        except Exception:
            logger.warning(
                "tm_sync_failed",
                extra={"tenant_id": str(tenant_id), "action": action},
                exc_info=True,
            )

    async def _record_event(
        self,
        *,
        tenant_id: uuid.UUID,
        from_status: TenantLifecycleStatus | None,
        to_status: TenantLifecycleStatus,
        transition: TransitionType,
        reason: str | None,
        performed_by: uuid.UUID | None,
        source: str,
    ) -> TenantLifecycleEvent:
        event = TenantLifecycleEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            from_status=from_status.value if from_status is not None else None,
            to_status=to_status.value,
            transition=transition.value,
            reason=reason,
            performed_by=performed_by,
            source=source,
        )
        return await self._event_repo.create(event)


# Mapping: TL transition → TM action name (None = no TM sync needed)
_TL_TO_TM_ACTION: dict[TransitionType, str | None] = {
    TransitionType.PROVISION: "provision",
    TransitionType.PEND: None,  # TM was left in provisioning; sync on ACTIVATE
    TransitionType.ACTIVATE: "activate",
    TransitionType.SUSPEND: "suspend",
    TransitionType.REACTIVATE: "activate",
    TransitionType.LOCK: "suspend",  # TM has no locked state; proxy as suspend
    TransitionType.UNLOCK: "activate",
    TransitionType.ARCHIVE: "archive",
    TransitionType.DELETE: "delete",
}
