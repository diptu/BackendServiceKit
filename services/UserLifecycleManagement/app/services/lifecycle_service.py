"""LifecycleService — the state machine on top of UserManagement's identity record.

One internal `_transition` backs every public named action. Each call:
1. Fail-fast fetches the remote user from UserManagement (confirms it
   exists, and bootstraps this service's local state on first use from
   UserManagement's own current status if no local row exists yet).
2. Validates the transition against VALID_TRANSITIONS.
3. Persists the local LifecycleState + a LifecycleEvent audit row.
4. Fire-and-log syncs the new status back to UserManagement — never
   blocks or fails the response if that sync doesn't land.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import VALID_TRANSITIONS, EventType, LifecycleStatus
from app.domain.exceptions import InvalidLifecycleTransitionError
from app.infrastructure.clients.user_lifecycle_client import (
    RemoteUser,
    UserLifecycleClient,
)
from app.models.lifecycle_event import LifecycleEvent
from app.models.lifecycle_state import LifecycleState
from app.repositories.base import PageResult
from app.repositories.lifecycle_event import LifecycleEventRepository
from app.repositories.lifecycle_state import LifecycleStateRepository


class LifecycleStatusView:
    """Aggregate view returned by get_status: UserManagement's own record
    merged with this service's locked/audit metadata."""

    def __init__(
        self,
        remote: RemoteUser,
        lifecycle_status: LifecycleStatus,
        locked_reason: str | None,
        locked_by: uuid.UUID | None,
        last_event: LifecycleEvent | None,
    ) -> None:
        self.user_id = remote.id
        self.tenant_id = remote.tenant_id
        self.email = remote.email
        self.display_name = remote.display_name
        self.remote_status = remote.status
        self.lifecycle_status = lifecycle_status
        self.deleted_at = remote.deleted_at
        self.locked_reason = locked_reason
        self.locked_by = locked_by
        self.last_event = last_event


class LifecycleService:
    def __init__(
        self,
        session: AsyncSession,
        client: UserLifecycleClient | None = None,
    ) -> None:
        self._session = session
        self._state_repo = LifecycleStateRepository(session)
        self._event_repo = LifecycleEventRepository(session)
        self._client = client or UserLifecycleClient()

    async def _transition(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        to_status: LifecycleStatus,
        event_type: EventType,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        locked_reason: str | None = None,
        locked_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        remote = await self._client.get_user(user_id, tenant_id)

        state = await self._state_repo.get_by_user_id(user_id)
        from_status: LifecycleStatus = LifecycleStatus(
            state.status if state is not None else remote.status
        )
        if state is None:
            state = LifecycleState(
                user_id=user_id, tenant_id=tenant_id, status=from_status
            )

        if to_status not in VALID_TRANSITIONS[from_status]:
            raise InvalidLifecycleTransitionError(from_status, to_status)

        state.status = to_status
        state.locked_reason = (
            locked_reason if to_status == LifecycleStatus.LOCKED else None
        )
        state.locked_by = locked_by if to_status == LifecycleStatus.LOCKED else None
        saved = await self._state_repo.save(state)

        await self._event_repo.create(
            LifecycleEvent(
                id=uuid.uuid4(),
                user_id=user_id,
                tenant_id=tenant_id,
                event_type=event_type,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                performed_by=performed_by,
            )
        )

        await self._client.sync_status(user_id, tenant_id, to_status)
        return saved

    async def activate(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.ACTIVE,
            EventType.ACTIVATE,
            reason=reason,
            performed_by=performed_by,
        )

    async def onboard(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.ACTIVE,
            EventType.ONBOARD,
            reason=reason,
            performed_by=performed_by,
        )

    async def deactivate(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.DEACTIVATED,
            EventType.DEACTIVATE,
            reason=reason,
            performed_by=performed_by,
        )

    async def offboard(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.DEACTIVATED,
            EventType.OFFBOARD,
            reason=reason,
            performed_by=performed_by,
        )

    async def suspend(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.SUSPENDED,
            EventType.SUSPEND,
            reason=reason,
            performed_by=performed_by,
        )

    async def unsuspend(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.ACTIVE,
            EventType.UNSUSPEND,
            reason=reason,
            performed_by=performed_by,
        )

    async def lock(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        locked_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.LOCKED,
            EventType.LOCK,
            reason=reason,
            performed_by=locked_by,
            locked_reason=reason,
            locked_by=locked_by,
        )

    async def unlock(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> LifecycleState:
        return await self._transition(
            user_id,
            tenant_id,
            LifecycleStatus.ACTIVE,
            EventType.UNLOCK,
            reason=reason,
            performed_by=performed_by,
        )

    async def restore(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        performed_by: uuid.UUID | None = None,
    ) -> RemoteUser:
        """Doesn't go through _transition/VALID_TRANSITIONS — restore isn't
        part of this service's local state machine, it undoes a
        UserManagement-level delete this service was never notified of."""
        restored = await self._client.restore_user(user_id, tenant_id)

        await self._event_repo.create(
            LifecycleEvent(
                id=uuid.uuid4(),
                user_id=user_id,
                tenant_id=tenant_id,
                event_type=EventType.RESTORE,
                from_status=None,
                to_status=restored.status,
                reason=None,
                performed_by=performed_by,
            )
        )
        return restored

    async def get_status(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> LifecycleStatusView:
        remote = await self._client.get_user(user_id, tenant_id)
        state = await self._state_repo.get_by_user_id(user_id)
        last_event = await self._event_repo.get_latest_by_user(user_id)

        lifecycle_status = (
            LifecycleStatus(state.status)
            if state is not None
            else LifecycleStatus(remote.status)
        )
        return LifecycleStatusView(
            remote=remote,
            lifecycle_status=lifecycle_status,
            locked_reason=state.locked_reason if state is not None else None,
            locked_by=state.locked_by if state is not None else None,
            last_event=last_event,
        )

    async def list_events(
        self, user_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> PageResult[LifecycleEvent]:
        return await self._event_repo.list_by_user(user_id, cursor=cursor, limit=limit)
