"""PolicyRepository — AbacPolicy CRUD + the tenant/resource/action lookup used by evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.models.policy import AbacPolicy
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class PolicyFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class PolicyRepository(BaseRepository[AbacPolicy]):
    async def create(self, policy: AbacPolicy) -> AbacPolicy:
        self._session.add(policy)
        await self._session.flush()
        await self._session.refresh(policy)
        return policy

    async def save(self, policy: AbacPolicy) -> AbacPolicy:
        self._session.add(policy)
        await self._session.flush()
        await self._session.refresh(policy)
        return policy

    async def soft_delete(self, policy: AbacPolicy) -> None:
        policy.deleted_at = datetime.now(timezone.utc)
        policy.is_active = False
        self._session.add(policy)
        await self._session.flush()

    async def get_by_id(
        self,
        policy_id: UUID,
        *,
        tenant_id: UUID,
        include_deleted: bool = False,
    ) -> AbacPolicy | None:
        stmt = select(AbacPolicy).where(
            AbacPolicy.id == policy_id, AbacPolicy.tenant_id == tenant_id
        )
        if not include_deleted:
            stmt = stmt.where(AbacPolicy.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, tenant_id: UUID, name: str) -> bool:
        result = await self._session.scalar(
            select(func.count(AbacPolicy.id))
            .where(AbacPolicy.tenant_id == tenant_id)
            .where(AbacPolicy.name == name)
            .where(AbacPolicy.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: PolicyFilter) -> int:
        filtered: Select[tuple[AbacPolicy]] = select(AbacPolicy).where(
            AbacPolicy.tenant_id == filters.tenant_id,
            AbacPolicy.deleted_at.is_(None),
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    async def list_matching(
        self, tenant_id: UUID, *, resource_type: str, action: str
    ) -> list[AbacPolicy]:
        """Active policies for tenant+resource_type+action, evaluation order.

        Ordered by priority DESC first; at equal priority, 'deny' sorts
        before 'allow' (alphabetically 'deny' < 'allow') so an explicit
        deny wins a tie rather than an allow — the safer default. Final
        tiebreak is most-recently-created first.
        """
        stmt = (
            select(AbacPolicy)
            .where(
                AbacPolicy.tenant_id == tenant_id,
                AbacPolicy.resource_type == resource_type,
                AbacPolicy.action == action,
                AbacPolicy.is_active.is_(True),
                AbacPolicy.deleted_at.is_(None),
            )
            .order_by(
                AbacPolicy.priority.desc(),
                AbacPolicy.effect.asc(),
                AbacPolicy.created_at.desc(),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars())

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[AbacPolicy]], filters: PolicyFilter
    ) -> Select[tuple[AbacPolicy]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(AbacPolicy.name.ilike(term))
        return stmt

    # ------------------------------------------------------------------
    # Paginated listing — defined last: a method literally named `list`
    # shadows the builtin `list` type for annotations later in this same
    # class body, so every `list[X]` return type above must be resolved
    # before this method is bound.
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        filters: PolicyFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AbacPolicy]:
        total = await self.count(filters)

        stmt: Select[tuple[AbacPolicy]] = select(AbacPolicy).where(
            AbacPolicy.tenant_id == filters.tenant_id,
            AbacPolicy.deleted_at.is_(None),
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    AbacPolicy.created_at < cursor_dt,
                    and_(AbacPolicy.created_at == cursor_dt, AbacPolicy.id < cursor_id),
                )
            )

        stmt = stmt.order_by(AbacPolicy.created_at.desc(), AbacPolicy.id.desc()).limit(
            limit + 1
        )

        result = await self._session.execute(stmt)
        rows: list[AbacPolicy] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )
