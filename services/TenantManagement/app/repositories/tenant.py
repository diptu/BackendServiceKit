"""TenantRepository — primary CRUD and query access for the Tenant entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TenantStatus
from app.models.tenant import Tenant
from app.repositories.base import BaseRepository, PageResult, decode_cursor, encode_cursor


@dataclass
class TenantFilter:
    """Filter parameters for :meth:`TenantRepository.list`."""

    status: TenantStatus | None = None
    region: str | None = None
    search: str | None = field(
        default=None,
        metadata={"description": "Substring match against name and display_name."},
    )


class TenantRepository(BaseRepository[Tenant]):
    """All database operations for the Tenant aggregate root."""

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, tenant: Tenant) -> Tenant:
        """Persist a new tenant and return it with server-side defaults populated."""
        self._session.add(tenant)
        await self._session.flush()
        await self._session.refresh(tenant)
        return tenant

    async def save(self, tenant: Tenant) -> Tenant:
        """Flush in-memory changes on a tracked tenant to the database."""
        self._session.add(tenant)
        await self._session.flush()
        await self._session.refresh(tenant)
        return tenant

    async def soft_delete(self, tenant: Tenant) -> None:
        """Mark a tenant as deleted without removing the row.

        Sets ``deleted_at`` to now and ``status`` to ``deleted``.
        """
        tenant.deleted_at = datetime.now(timezone.utc)
        tenant.status = TenantStatus.DELETED
        self._session.add(tenant)
        await self._session.flush()

    async def restore(self, tenant: Tenant) -> Tenant:
        """Undo a soft-delete by clearing ``deleted_at``.

        The caller is responsible for setting the correct ``status``
        before calling this method.
        """
        tenant.deleted_at = None
        self._session.add(tenant)
        await self._session.flush()
        await self._session.refresh(tenant)
        return tenant

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        tenant_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Tenant | None:
        """Return the tenant with the given ID, or ``None`` if not found.

        Args:
            tenant_id: Primary key of the tenant.
            include_deleted: When ``True``, soft-deleted tenants are included.
        """
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(Tenant.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Tenant | None:
        """Return the tenant with the given slug, or ``None``.

        Includes soft-deleted tenants so name uniqueness can be enforced.
        """
        result = await self._session.execute(
            select(Tenant).where(Tenant.name == name)
        )
        return result.scalar_one_or_none()

    async def exists_by_name(self, name: str) -> bool:
        """Return ``True`` if any tenant (including deleted) owns this slug."""
        result = await self._session.scalar(
            select(func.count(Tenant.id)).where(Tenant.name == name)
        )
        return (result or 0) > 0

    async def exists_by_id(self, tenant_id: UUID) -> bool:
        """Return ``True`` if an active (non-deleted) tenant has this ID."""
        result = await self._session.scalar(
            select(func.count(Tenant.id))
            .where(Tenant.id == tenant_id)
            .where(Tenant.deleted_at.is_(None))
        )
        return (result or 0) > 0

    # ------------------------------------------------------------------
    # List / search / pagination
    # ------------------------------------------------------------------

    async def count(self, filters: TenantFilter | None = None) -> int:
        """Return total tenants matching ``filters`` (excludes deleted)."""
        stmt = select(func.count(Tenant.id)).where(Tenant.deleted_at.is_(None))
        stmt = self._apply_filters(stmt, filters)
        result = await self._session.scalar(stmt)
        return result or 0

    async def list(
        self,
        *,
        filters: TenantFilter | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Tenant]:
        """Return a cursor-paginated page of tenants.

        Pagination strategy: keyset on ``(created_at DESC, id DESC)``.
        The returned :class:`PageResult` contains the encoded cursor for the
        next page when ``has_more`` is ``True``.

        Args:
            filters: Optional field-level filters.
            cursor:  Opaque cursor from the previous response. ``None`` for the
                     first page.
            limit:   Maximum results per page (1–100).

        Returns:
            :class:`PageResult` with items, total count, next cursor, and
            ``has_more`` flag.
        """
        total = await self.count(filters)

        stmt: Select[tuple[Tenant]] = (
            select(Tenant).where(Tenant.deleted_at.is_(None))
        )
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

        stmt = (
            stmt
            .order_by(Tenant.created_at.desc(), Tenant.id.desc())
            .limit(limit + 1)
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
