"""GroupService — Group CRUD + group<->user membership."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateGroupCmd, UpdateGroupCmd
from app.domain.enums import EntityStatus
from app.domain.exceptions import (
    GroupMembershipAlreadyExistsError,
    GroupMembershipNotFoundError,
    GroupNameConflictError,
    GroupNotFoundError,
)
from app.models.group import Group
from app.repositories.base import PageResult
from app.repositories.group import GroupFilter, GroupRepository


class GroupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GroupRepository(session)

    async def create(self, cmd: CreateGroupCmd) -> Group:
        if await self._repo.exists_by_name(cmd.tenant_id, cmd.name):
            raise GroupNameConflictError(cmd.tenant_id, cmd.name)

        group = Group(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            description=cmd.description,
            status=EntityStatus.ACTIVE,
        )
        return await self._repo.create(group)

    async def get(self, group_id: uuid.UUID, tenant_id: uuid.UUID) -> Group:
        group = await self._repo.get_by_id(group_id, tenant_id=tenant_id)
        if group is None:
            raise GroupNotFoundError(group_id)
        return group

    async def update(
        self, group_id: uuid.UUID, tenant_id: uuid.UUID, cmd: UpdateGroupCmd
    ) -> Group:
        group = await self.get(group_id, tenant_id)

        if cmd.name is not None and cmd.name != group.name:
            if await self._repo.exists_by_name(tenant_id, cmd.name):
                raise GroupNameConflictError(tenant_id, cmd.name)
            group.name = cmd.name
        if cmd.description is not None:
            group.description = cmd.description

        return await self._repo.save(group)

    async def delete(self, group_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        group = await self.get(group_id, tenant_id)
        if group.deleted_at is not None:
            return
        await self._repo.soft_delete(group)

    # ------------------------------------------------------------------
    # Group <-> User membership
    # ------------------------------------------------------------------

    async def add_member(
        self, group_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get(group_id, tenant_id)
        if await self._repo.has_member(group_id, user_id):
            raise GroupMembershipAlreadyExistsError(group_id, user_id)
        await self._repo.add_member(group_id, user_id)

    async def remove_member(
        self, group_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get(group_id, tenant_id)
        if not await self._repo.has_member(group_id, user_id):
            raise GroupMembershipNotFoundError(group_id, user_id)
        await self._repo.remove_member(group_id, user_id)

    async def list_members(
        self, group_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[uuid.UUID]:
        await self.get(group_id, tenant_id)
        return await self._repo.list_members(group_id)

    # ------------------------------------------------------------------
    # Paginated listing — defined last: a method literally named `list`
    # shadows the builtin `list` type for annotations later in this same
    # class body, so every `list[X]` return type above must be resolved
    # before this method is bound.
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Group]:
        filters = GroupFilter(tenant_id=tenant_id, search=search)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)
