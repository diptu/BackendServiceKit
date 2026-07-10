"""UserRepository — primary CRUD and query access for the User entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.models.user import User
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class UserFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class UserRepository(BaseRepository[User]):
    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(timezone.utc)
        self._session.add(user)
        await self._session.flush()

    async def restore(self, user: User) -> User:
        user.deleted_at = None
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_id(
        self,
        user_id: UUID,
        *,
        tenant_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_email(self, tenant_id: UUID, email: str) -> bool:
        result = await self._session.scalar(
            select(func.count(User.id))
            .where(User.tenant_id == tenant_id)
            .where(User.email == email)
            .where(User.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: UserFilter) -> int:
        filtered: Select[tuple[User]] = select(User).where(
            User.tenant_id == filters.tenant_id,
            User.deleted_at.is_(None),
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[User]], filters: UserFilter
    ) -> Select[tuple[User]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                )
            )
        return stmt

    async def list(
        self,
        *,
        filters: UserFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[User]:
        total = await self.count(filters)

        stmt: Select[tuple[User]] = select(User).where(
            User.tenant_id == filters.tenant_id,
            User.deleted_at.is_(None),
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    User.created_at < cursor_dt,
                    and_(User.created_at == cursor_dt, User.id < cursor_id),
                )
            )

        stmt = stmt.order_by(User.created_at.desc(), User.id.desc()).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[User] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )
