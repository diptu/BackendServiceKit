"""RoleService — Role CRUD, role<->permission linkage, user<->role assignment."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateRoleCmd, UpdateRoleCmd
from app.domain.enums import EntityStatus
from app.domain.exceptions import (
    PermissionNotFoundError,
    RoleNameConflictError,
    RoleNotFoundError,
    RolePermissionAlreadyAssignedError,
    RolePermissionNotAssignedError,
    UserRoleAlreadyAssignedError,
    UserRoleNotAssignedError,
)
from app.models.permission import Permission
from app.models.role import Role
from app.repositories.base import PageResult
from app.repositories.permission import PermissionRepository
from app.repositories.role import RoleFilter, RoleRepository


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._role_repo = RoleRepository(session)
        self._permission_repo = PermissionRepository(session)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, cmd: CreateRoleCmd) -> Role:
        if await self._role_repo.exists_by_name(cmd.tenant_id, cmd.name):
            raise RoleNameConflictError(cmd.tenant_id, cmd.name)

        role = Role(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            description=cmd.description,
            status=EntityStatus.ACTIVE,
        )
        return await self._role_repo.create(role)

    async def get(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Role:
        role = await self._role_repo.get_by_id(role_id, tenant_id=tenant_id)
        if role is None:
            raise RoleNotFoundError(role_id)
        return role

    async def update(
        self, role_id: uuid.UUID, tenant_id: uuid.UUID, cmd: UpdateRoleCmd
    ) -> Role:
        role = await self.get(role_id, tenant_id)

        if cmd.name is not None and cmd.name != role.name:
            if await self._role_repo.exists_by_name(tenant_id, cmd.name):
                raise RoleNameConflictError(tenant_id, cmd.name)
            role.name = cmd.name
        if cmd.description is not None:
            role.description = cmd.description

        return await self._role_repo.save(role)

    async def delete(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        role = await self.get(role_id, tenant_id)
        if role.deleted_at is not None:
            return
        await self._role_repo.soft_delete(role)

    # ------------------------------------------------------------------
    # Role <-> Permission linkage
    # ------------------------------------------------------------------

    async def add_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get(role_id, tenant_id)
        permission = await self._permission_repo.get_by_id(
            permission_id, tenant_id=tenant_id
        )
        if permission is None:
            raise PermissionNotFoundError(permission_id)

        if await self._role_repo.has_permission(role_id, permission_id):
            raise RolePermissionAlreadyAssignedError(role_id, permission_id)

        await self._role_repo.add_permission(role_id, permission_id)

    async def remove_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get(role_id, tenant_id)
        if not await self._role_repo.has_permission(role_id, permission_id):
            raise RolePermissionNotAssignedError(role_id, permission_id)
        await self._role_repo.remove_permission(role_id, permission_id)

    async def list_permissions(
        self, role_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[Permission]:
        await self.get(role_id, tenant_id)
        return await self._role_repo.list_permissions(role_id)

    # ------------------------------------------------------------------
    # User <-> Role assignment
    # ------------------------------------------------------------------

    async def assign_to_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get(role_id, tenant_id)
        if await self._role_repo.has_role(user_id, role_id):
            raise UserRoleAlreadyAssignedError(user_id, role_id)
        await self._role_repo.assign_to_user(user_id, role_id, tenant_id)

    async def unassign_from_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get(role_id, tenant_id)
        if not await self._role_repo.has_role(user_id, role_id):
            raise UserRoleNotAssignedError(user_id, role_id)
        await self._role_repo.unassign_from_user(user_id, role_id)

    async def list_roles_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[Role]:
        return await self._role_repo.list_for_user(user_id, tenant_id)

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
    ) -> PageResult[Role]:
        filters = RoleFilter(tenant_id=tenant_id, search=search)
        return await self._role_repo.list(filters=filters, cursor=cursor, limit=limit)
