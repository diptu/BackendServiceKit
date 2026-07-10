"""PermissionRepository — Permission CRUD."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.domain.enums import EntityStatus
from app.models.permission import Permission
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class PermissionFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class PermissionRepository(BaseRepository[Permission]):
    async def create(self, permission: Permission) -> Permission:
        self._session.add(permission)
        await self._session.flush()
        await self._session.refresh(permission)
        return permission

    async def save(self, permission: Permission) -> Permission:
        self._session.add(permission)
        await self._session.flush()
        await self._session.refresh(permission)
        return permission

    async def soft_delete(self, permission: Permission) -> None:
        permission.deleted_at = datetime.now(timezone.utc)
        permission.status = EntityStatus.DELETED
        self._session.add(permission)
        await self._session.flush()

    async def get_by_id(
        self,
        permission_id: UUID,
        *,
        tenant_id: UUID,
        include_deleted: bool = False,
    ) -> Permission | None:
        stmt = select(Permission).where(
            Permission.id == permission_id, Permission.tenant_id == tenant_id
        )
        if not include_deleted:
            stmt = stmt.where(Permission.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, tenant_id: UUID, name: str) -> bool:
        result = await self._session.scalar(
            select(func.count(Permission.id))
            .where(Permission.tenant_id == tenant_id)
            .where(Permission.name == name)
            .where(Permission.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: PermissionFilter) -> int:
        filtered: Select[tuple[Permission]] = select(Permission).where(
            Permission.tenant_id == filters.tenant_id,
            Permission.deleted_at.is_(None),
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    async def list(
        self,
        *,
        filters: PermissionFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Permission]:
        total = await self.count(filters)

        stmt: Select[tuple[Permission]] = select(Permission).where(
            Permission.tenant_id == filters.tenant_id,
            Permission.deleted_at.is_(None),
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Permission.created_at < cursor_dt,
                    and_(Permission.created_at == cursor_dt, Permission.id < cursor_id),
                )
            )

        stmt = stmt.order_by(Permission.created_at.desc(), Permission.id.desc()).limit(
            limit + 1
        )

        result = await self._session.execute(stmt)
        rows: list[Permission] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[Permission]], filters: PermissionFilter
    ) -> Select[tuple[Permission]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(Permission.name.ilike(term))
        return stmt
