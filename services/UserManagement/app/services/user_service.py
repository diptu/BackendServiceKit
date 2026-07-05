"""UserService — User CRUD, status lifecycle, audit trail, event publishing."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateUserCmd, UpdateUserCmd
from app.domain.enums import VALID_TRANSITIONS, UserStatus
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
        *,
        reason: str | None = None,
        performed_by: uuid.UUID | None = None,
    ) -> User:
        user = await self.get(user_id, tenant_id)
        from_status = UserStatus(user.status)

        if to_status not in VALID_TRANSITIONS[from_status]:
            raise InvalidUserStatusTransitionError(from_status, to_status)

        user.status = to_status
        saved = await self._repo.save(user)

        await self._history_repo.create(
            UserStatusHistory(
                id=uuid.uuid4(),
                user_id=user_id,
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
