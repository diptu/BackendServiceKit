"""PermissionService — Permission CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreatePermissionCmd, UpdatePermissionCmd
from app.domain.enums import EntityStatus
from app.domain.exceptions import PermissionNameConflictError, PermissionNotFoundError
from app.models.permission import Permission
from app.repositories.base import PageResult
from app.repositories.permission import PermissionFilter, PermissionRepository


class PermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PermissionRepository(session)

    async def create(self, cmd: CreatePermissionCmd) -> Permission:
        if await self._repo.exists_by_name(cmd.tenant_id, cmd.name):
            raise PermissionNameConflictError(cmd.tenant_id, cmd.name)

        permission = Permission(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            description=cmd.description,
            status=EntityStatus.ACTIVE,
        )
        return await self._repo.create(permission)

    async def get(self, permission_id: uuid.UUID, tenant_id: uuid.UUID) -> Permission:
        permission = await self._repo.get_by_id(permission_id, tenant_id=tenant_id)
        if permission is None:
            raise PermissionNotFoundError(permission_id)
        return permission

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        search: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Permission]:
        filters = PermissionFilter(tenant_id=tenant_id, search=search)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def update(
        self, permission_id: uuid.UUID, tenant_id: uuid.UUID, cmd: UpdatePermissionCmd
    ) -> Permission:
        permission = await self.get(permission_id, tenant_id)

        if cmd.name is not None and cmd.name != permission.name:
            if await self._repo.exists_by_name(tenant_id, cmd.name):
                raise PermissionNameConflictError(tenant_id, cmd.name)
            permission.name = cmd.name
        if cmd.description is not None:
            permission.description = cmd.description

        return await self._repo.save(permission)

    async def delete(self, permission_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        permission = await self.get(permission_id, tenant_id)
        if permission.deleted_at is not None:
            return
        await self._repo.soft_delete(permission)
