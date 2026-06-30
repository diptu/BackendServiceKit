"""TenantRepository — primary CRUD and query access for the Tenant entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.domain.enums import TenantStatus
from app.models.tenant import Tenant
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class TenantFilter:
    status: TenantStatus | None = None
    region: str | None = None
    search: str | None = field(default=None)


class TenantRepository(BaseRepository[Tenant]):
    async def create(self, tenant: Tenant) -> Tenant:
        self._session.add(tenant)
        await self._session.flush()
        await self._session.refresh(tenant)
        return tenant

    async def save(self, tenant: Tenant) -> Tenant:
        self._session.add(tenant)
        await self._session.flush()
        await self._session.refresh(tenant)
        return tenant

    async def soft_delete(self, tenant: Tenant) -> None:
        tenant.deleted_at = datetime.now(timezone.utc)
        tenant.status = TenantStatus.DELETED
        self._session.add(tenant)
        await self._session.flush()

    async def restore(self, tenant: Tenant) -> Tenant:
        tenant.deleted_at = None
        self._session.add(tenant)
        await self._session.flush()
        await self._session.refresh(tenant)
        return tenant

    async def get_by_id(
        self,
        tenant_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(Tenant.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Tenant | None:
        result = await self._session.execute(select(Tenant).where(Tenant.name == name))
        return result.scalar_one_or_none()

    async def exists_by_name(self, name: str) -> bool:
        result = await self._session.scalar(
            select(func.count(Tenant.id)).where(Tenant.name == name)
        )
        return (result or 0) > 0

    async def exists_by_id(self, tenant_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count(Tenant.id))
            .where(Tenant.id == tenant_id)
            .where(Tenant.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: TenantFilter | None = None) -> int:
        filtered: Select[tuple[Tenant]] = select(Tenant).where(
            Tenant.deleted_at.is_(None)
        )
        filtered = self._apply_filters(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    async def list(
        self,
        *,
        filters: TenantFilter | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Tenant]:
        total = await self.count(filters)

        stmt: Select[tuple[Tenant]] = select(Tenant).where(Tenant.deleted_at.is_(None))
        stmt = self._apply_filters(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Tenant.created_at < cursor_dt,
                    and_(
                        Tenant.created_at == cursor_dt,
                        Tenant.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(Tenant.created_at.desc(), Tenant.id.desc()).limit(
            limit + 1
        )

        result = await self._session.execute(stmt)
        rows: list[Tenant] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items,
            total=total,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Tenant]],
        filters: TenantFilter | None,
    ) -> Select[tuple[Tenant]]:
        if filters is None:
            return stmt
        if filters.status is not None:
            stmt = stmt.where(Tenant.status == filters.status.value)
        if filters.region is not None:
            stmt = stmt.where(Tenant.region == filters.region)
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    Tenant.name.ilike(term),
                    Tenant.display_name.ilike(term),
                )
            )
        return stmt
