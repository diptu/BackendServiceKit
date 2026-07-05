"""EntitlementRepository — user-scoped entitlement CRUD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.domain.enums import EntitlementStatus
from app.models.entitlement import Entitlement
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class EntitlementFilter:
    tenant_id: UUID


class EntitlementRepository(BaseRepository[Entitlement]):
    async def create(self, entitlement: Entitlement) -> Entitlement:
        self._session.add(entitlement)
        await self._session.flush()
        await self._session.refresh(entitlement)
        return entitlement

    async def soft_delete(self, entitlement: Entitlement) -> None:
        entitlement.deleted_at = datetime.now(timezone.utc)
        entitlement.status = EntitlementStatus.REVOKED
        self._session.add(entitlement)
        await self._session.flush()

    async def get_by_id(
        self, entitlement_id: UUID, *, tenant_id: UUID | None = None
    ) -> Entitlement | None:
        stmt = select(Entitlement).where(
            Entitlement.id == entitlement_id, Entitlement.deleted_at.is_(None)
        )
        if tenant_id is not None:
            stmt = stmt.where(Entitlement.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, filters: EntitlementFilter) -> int:
        result = await self._session.scalar(
            select(func.count(Entitlement.id))
            .where(Entitlement.tenant_id == filters.tenant_id)
            .where(Entitlement.deleted_at.is_(None))
        )
        return result or 0

    async def list(
        self,
        *,
        filters: EntitlementFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Entitlement]:
        total = await self.count(filters)

        stmt: Select[tuple[Entitlement]] = select(Entitlement).where(
            Entitlement.tenant_id == filters.tenant_id,
            Entitlement.deleted_at.is_(None),
        )

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Entitlement.created_at < cursor_dt,
                    and_(
                        Entitlement.created_at == cursor_dt, Entitlement.id < cursor_id
                    ),
                )
            )

        stmt = stmt.order_by(
            Entitlement.created_at.desc(), Entitlement.id.desc()
        ).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[Entitlement] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )
