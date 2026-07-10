"""GroupRepository — Group CRUD + group<->user membership."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, delete, func, or_, select

from app.domain.enums import EntityStatus
from app.models.group import Group, GroupMembership
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class GroupFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class GroupRepository(BaseRepository[Group]):
    async def create(self, group: Group) -> Group:
        self._session.add(group)
        await self._session.flush()
        await self._session.refresh(group)
        return group

    async def save(self, group: Group) -> Group:
        self._session.add(group)
        await self._session.flush()
        await self._session.refresh(group)
        return group

    async def soft_delete(self, group: Group) -> None:
        group.deleted_at = datetime.now(timezone.utc)
        group.status = EntityStatus.DELETED
        self._session.add(group)
        await self._session.flush()

    async def get_by_id(
        self,
        group_id: UUID,
        *,
        tenant_id: UUID,
        include_deleted: bool = False,
    ) -> Group | None:
        stmt = select(Group).where(Group.id == group_id, Group.tenant_id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(Group.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, tenant_id: UUID, name: str) -> bool:
        result = await self._session.scalar(
            select(func.count(Group.id))
            .where(Group.tenant_id == tenant_id)
            .where(Group.name == name)
            .where(Group.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: GroupFilter) -> int:
        filtered: Select[tuple[Group]] = select(Group).where(
            Group.tenant_id == filters.tenant_id,
            Group.deleted_at.is_(None),
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[Group]], filters: GroupFilter
    ) -> Select[tuple[Group]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(Group.name.ilike(term))
        return stmt

    # ------------------------------------------------------------------
    # Group <-> User membership
    # ------------------------------------------------------------------

    async def has_member(self, group_id: UUID, user_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(GroupMembership)
            .where(
                GroupMembership.group_id == group_id, GroupMembership.user_id == user_id
            )
        )
        return (result or 0) > 0

    async def add_member(self, group_id: UUID, user_id: UUID) -> None:
        self._session.add(GroupMembership(group_id=group_id, user_id=user_id))
        await self._session.flush()

    async def remove_member(self, group_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(GroupMembership).where(
                GroupMembership.group_id == group_id, GroupMembership.user_id == user_id
            )
        )
        await self._session.flush()

    async def list_members(self, group_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(GroupMembership.user_id)
            .where(GroupMembership.group_id == group_id)
            .order_by(GroupMembership.created_at.desc())
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
        filters: GroupFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Group]:
        total = await self.count(filters)

        stmt: Select[tuple[Group]] = select(Group).where(
            Group.tenant_id == filters.tenant_id,
            Group.deleted_at.is_(None),
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Group.created_at < cursor_dt,
                    and_(Group.created_at == cursor_dt, Group.id < cursor_id),
                )
            )

        stmt = stmt.order_by(Group.created_at.desc(), Group.id.desc()).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[Group] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )
