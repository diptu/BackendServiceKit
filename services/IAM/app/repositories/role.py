"""RoleRepository — Role CRUD, role<->permission linkage, user<->role assignment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, delete, func, or_, select

from app.domain.enums import EntityStatus
from app.models.membership import UserRole
from app.models.permission import Permission, RolePermission
from app.models.role import Role
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class RoleFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class RoleRepository(BaseRepository[Role]):
    async def create(self, role: Role) -> Role:
        self._session.add(role)
        await self._session.flush()
        await self._session.refresh(role)
        return role

    async def save(self, role: Role) -> Role:
        self._session.add(role)
        await self._session.flush()
        await self._session.refresh(role)
        return role

    async def soft_delete(self, role: Role) -> None:
        role.deleted_at = datetime.now(timezone.utc)
        role.status = EntityStatus.DELETED
        self._session.add(role)
        await self._session.flush()

    async def get_by_id(
        self,
        role_id: UUID,
        *,
        tenant_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> Role | None:
        stmt = select(Role).where(Role.id == role_id)
        if tenant_id is not None:
            stmt = stmt.where(Role.tenant_id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(Role.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, tenant_id: UUID, name: str) -> bool:
        result = await self._session.scalar(
            select(func.count(Role.id))
            .where(Role.tenant_id == tenant_id)
            .where(Role.name == name)
            .where(Role.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: RoleFilter) -> int:
        filtered: Select[tuple[Role]] = select(Role).where(
            Role.tenant_id == filters.tenant_id,
            Role.deleted_at.is_(None),
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[Role]], filters: RoleFilter
    ) -> Select[tuple[Role]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(Role.name.ilike(term))
        return stmt

    # ------------------------------------------------------------------
    # Role <-> Permission linkage
    # ------------------------------------------------------------------

    async def has_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(RolePermission)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        return (result or 0) > 0

    async def add_permission(self, role_id: UUID, permission_id: UUID) -> None:
        self._session.add(RolePermission(role_id=role_id, permission_id=permission_id))
        await self._session.flush()

    async def remove_permission(self, role_id: UUID, permission_id: UUID) -> None:
        await self._session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        await self._session.flush()

    async def list_permissions(self, role_id: UUID) -> list[Permission]:
        result = await self._session.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id, Permission.deleted_at.is_(None))
            .order_by(Permission.name)
        )
        return list(result.scalars())

    # ------------------------------------------------------------------
    # User <-> Role assignment
    # ------------------------------------------------------------------

    async def has_role(self, user_id: UUID, role_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(UserRole)
            .where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        return (result or 0) > 0

    async def assign_to_user(
        self, user_id: UUID, role_id: UUID, tenant_id: UUID
    ) -> None:
        self._session.add(
            UserRole(user_id=user_id, role_id=role_id, tenant_id=tenant_id)
        )
        await self._session.flush()

    async def unassign_from_user(self, user_id: UUID, role_id: UUID) -> None:
        await self._session.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        )
        await self._session.flush()

    async def list_for_user(self, user_id: UUID, tenant_id: UUID) -> list[Role]:
        result = await self._session.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Role.deleted_at.is_(None),
            )
            .order_by(Role.name)
        )
        return list(result.scalars())

    # ------------------------------------------------------------------
    # Paginated listing — defined last: a method literally named `list`
    # shadows the builtin `list` type for annotations later in this same
    # class body, so every `list[X]` return type above must be resolved
    # before this method is bound.
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        filters: RoleFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Role]:
        total = await self.count(filters)

        stmt: Select[tuple[Role]] = select(Role).where(
            Role.tenant_id == filters.tenant_id,
            Role.deleted_at.is_(None),
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Role.created_at < cursor_dt,
                    and_(Role.created_at == cursor_dt, Role.id < cursor_id),
                )
            )

        stmt = stmt.order_by(Role.created_at.desc(), Role.id.desc()).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[Role] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )
