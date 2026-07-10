"""UserService — User CRUD, status lifecycle, audit trail, event publishing.

Merges UserManagement's original CRUD/activate/suspend/deactivate/restore
with UserLifecycleManagement's richer transitions (lock/unlock/onboard/
offboard/unsuspend). Both used to be separate services connected over
HTTP — UserLifecycleManagement had to fail-fast fetch this service's user
record, validate transitions against its own local copy of the status, and
fire-and-log sync the result back over the network (accepting that the two
copies could drift if that last call failed). Now that it's one service,
one table, one transaction: there is only one `status` column, `_transition`
is the only place that changes it, and there is no possibility of drift
because there was never a second copy to drift from.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateUserCmd, UpdateUserCmd
from app.domain.enums import VALID_TRANSITIONS, StatusChangeAction, UserStatus
from app.domain.events import (
    UserCreated,
    UserDeleted,
    UserRestored,
    UserStatusChanged,
    UserUpdated,
)
from app.domain.exceptions import (
    InvalidUserStatusTransitionError,
    UserEmailConflictError,
    UserNotDeletedError,
    UserNotFoundError,
)
from app.infrastructure.messaging.publisher import NullPublisher, RabbitMQPublisher
from app.models.user import User
from app.models.user_status_history import UserStatusHistory
from app.repositories.base import PageResult
from app.repositories.user import UserFilter, UserRepository
from app.repositories.user_status_history import UserStatusHistoryRepository


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        publisher: RabbitMQPublisher | NullPublisher | None = None,
    ) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._history_repo = UserStatusHistoryRepository(session)
        self._publisher = publisher or NullPublisher()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, cmd: CreateUserCmd) -> User:
        if await self._repo.exists_by_email(cmd.tenant_id, cmd.email):
            raise UserEmailConflictError(cmd.tenant_id, cmd.email)

        user = User(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            email=cmd.email,
            first_name=cmd.first_name,
            last_name=cmd.last_name,
            status=UserStatus.PENDING,
        )
        await self._repo.create(user)

        await self._publisher.publish(
            "user.created",
            UserCreated(
                user_id=user.id,
                tenant_id=cmd.tenant_id,
                email=user.email,
                display_name=user.display_name,
                status=user.status,
            ),
        )
        return user

    async def get(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User:
        user = await self._repo.get_by_id(user_id, tenant_id=tenant_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[User]:
        filters = UserFilter(tenant_id=tenant_id, search=search)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def update(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, cmd: UpdateUserCmd
    ) -> User:
        user = await self.get(user_id, tenant_id)

        changed_fields: list[str] = []
        if cmd.email is not None and cmd.email != user.email:
            if await self._repo.exists_by_email(tenant_id, cmd.email):
                raise UserEmailConflictError(tenant_id, cmd.email)
            user.email = cmd.email
            changed_fields.append("email")
        if cmd.first_name is not None:
            user.first_name = cmd.first_name
            changed_fields.append("first_name")
        if cmd.last_name is not None:
            user.last_name = cmd.last_name
            changed_fields.append("last_name")

        saved = await self._repo.save(user)

        if changed_fields:
            await self._publisher.publish(
                "user.updated",
                UserUpdated(
                    user_id=user_id, tenant_id=tenant_id, changed_fields=changed_fields
                ),
            )
        return saved

    async def delete(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        user = await self.get(user_id, tenant_id)
        if user.deleted_at is not None:
            return
        await self._repo.soft_delete(user)
        await self._publisher.publish(
            "user.deleted", UserDeleted(user_id=user_id, tenant_id=tenant_id)
        )

    async def restore(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User:
        user = await self._repo.get_by_id(
            user_id, tenant_id=tenant_id, include_deleted=True
        )
        if user is None:
            raise UserNotFoundError(user_id)
        if user.deleted_at is None:
            raise UserNotDeletedError(user_id)

        restored = await self._repo.restore(user)
        await self._history_repo.create(
            UserStatusHistory(
                id=uuid.uuid4(),
                user_id=user_id,
                action=StatusChangeAction.RESTORE,
                from_status=None,
                to_status=restored.status,
            )
        )
        await self._publisher.publish(
            "user.restored", UserRestored(user_id=user_id, tenant_id=tenant_id)
        )
        return restored

    # ------------------------------------------------------------------
    # Status lifecycle
    # ------------------------------------------------------------------

    async def _transition(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        to_status: UserStatus,
        action: StatusChangeAction,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
        locked_reason: str | None = None,
        locked_by: uuid.UUID | None = None,
    ) -> User:
        user = await self.get(user_id, tenant_id)
        from_status = UserStatus(user.status)

        if to_status not in VALID_TRANSITIONS[from_status]:
            raise InvalidUserStatusTransitionError(from_status, to_status)

        user.status = to_status
        user.locked_reason = locked_reason if to_status == UserStatus.LOCKED else None
        user.locked_by = locked_by if to_status == UserStatus.LOCKED else None
        saved = await self._repo.save(user)

        await self._history_repo.create(
            UserStatusHistory(
                id=uuid.uuid4(),
                user_id=user_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                performed_by=performed_by,
            )
        )
        await self._publisher.publish(
            "user.status_changed",
            UserStatusChanged(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                performed_by=performed_by,
            ),
        )
        return saved

    async def activate(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.ACTIVE,
            StatusChangeAction.ACTIVATE,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.ACTIVE,
            StatusChangeAction.ONBOARD,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.SUSPENDED,
            StatusChangeAction.SUSPEND,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.ACTIVE,
            StatusChangeAction.UNSUSPEND,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.LOCKED,
            StatusChangeAction.LOCK,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.ACTIVE,
            StatusChangeAction.UNLOCK,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.DEACTIVATED,
            StatusChangeAction.DEACTIVATE,
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
    ) -> User:
        return await self._transition(
            user_id,
            tenant_id,
            UserStatus.DEACTIVATED,
            StatusChangeAction.OFFBOARD,
            reason=reason,
            performed_by=performed_by,
        )

    async def list_status_history(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[UserStatusHistory]:
        await self.get(user_id, tenant_id)
        return await self._history_repo.list_by_user(
            user_id, cursor=cursor, limit=limit
        )
