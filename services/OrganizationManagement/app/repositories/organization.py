"""OrganizationRepository — primary CRUD and query access for the Organization entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.domain.enums import OrganizationStatus
from app.models.organization import Organization
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class OrganizationFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class OrganizationRepository(BaseRepository[Organization]):
    async def create(self, organization: Organization) -> Organization:
        self._session.add(organization)
        await self._session.flush()
        await self._session.refresh(organization)
        return organization

    async def save(self, organization: Organization) -> Organization:
        self._session.add(organization)
        await self._session.flush()
        await self._session.refresh(organization)
        return organization

    async def soft_delete(self, organization: Organization) -> None:
        organization.deleted_at = datetime.now(timezone.utc)
        organization.status = OrganizationStatus.DELETED
        self._session.add(organization)
        await self._session.flush()

    async def get_by_id(
        self,
        organization_id: UUID,
        *,
        tenant_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> Organization | None:
        stmt = select(Organization).where(Organization.id == organization_id)
        if tenant_id is not None:
            stmt = stmt.where(Organization.tenant_id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(Organization.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_slug(self, tenant_id: UUID, slug: str) -> bool:
        result = await self._session.scalar(
            select(func.count(Organization.id))
            .where(Organization.tenant_id == tenant_id)
            .where(Organization.slug == slug)
            .where(Organization.deleted_at.is_(None))
        )
        return (result or 0) > 0

    async def count(self, filters: OrganizationFilter) -> int:
        filtered: Select[tuple[Organization]] = select(Organization).where(
            Organization.tenant_id == filters.tenant_id,
            Organization.deleted_at.is_(None),
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        result = await self._session.scalar(
            select(func.count(Organization.id))
            .where(Organization.tenant_id == tenant_id)
            .where(Organization.deleted_at.is_(None))
        )
        return result or 0

    async def list(
        self,
        *,
        filters: OrganizationFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Organization]:
        total = await self.count(filters)

        stmt: Select[tuple[Organization]] = select(Organization).where(
            Organization.tenant_id == filters.tenant_id,
            Organization.deleted_at.is_(None),
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Organization.created_at < cursor_dt,
                    and_(
                        Organization.created_at == cursor_dt,
                        Organization.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            Organization.created_at.desc(), Organization.id.desc()
        ).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[Organization] = list(result.scalars())

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
    def _apply_search(
        stmt: Select[tuple[Organization]],
        filters: OrganizationFilter,
    ) -> Select[tuple[Organization]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    Organization.name.ilike(term),
                    Organization.slug.ilike(term),
                )
            )
        return stmt
