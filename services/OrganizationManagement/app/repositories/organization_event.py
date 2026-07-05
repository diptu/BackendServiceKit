"""Repository for OrganizationEvent (append-only audit log).

Mirrors services/Tenent/app/repositories/lifecycle_event.py's shape exactly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.organization_event import OrganizationEvent
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


def _serialize(event: object) -> dict[str, object]:
    """Convert a flat domain event dataclass to a JSON-storable dict.

    None of this service's event dataclasses nest another dataclass, so a
    shallow `vars()` copy is equivalent to `dataclasses.asdict()` here
    without asdict's stricter (and here, unnecessary) DataclassInstance typing.
    """
    return {
        k: (str(v) if isinstance(v, (UUID, datetime)) else v)
        for k, v in vars(event).items()
    }


class OrganizationEventRepository(BaseRepository[OrganizationEvent]):
    async def create(self, event: OrganizationEvent) -> OrganizationEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def record(
        self,
        organization_id: UUID,
        tenant_id: UUID,
        event: object,
        *,
        performed_by: UUID | None = None,
    ) -> OrganizationEvent:
        """Serialize and persist a domain event dataclass as an audit-trail row."""
        row = OrganizationEvent(
            id=uuid.uuid4(),
            organization_id=organization_id,
            tenant_id=tenant_id,
            event_type=type(event).__name__,
            payload=_serialize(event),
            performed_by=performed_by,
        )
        return await self.create(row)

    async def list_by_organization(
        self,
        organization_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationEvent]:
        base_where = [OrganizationEvent.organization_id == organization_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(OrganizationEvent)
            .where(*base_where)
            .order_by(OrganizationEvent.occurred_at.desc(), OrganizationEvent.id.desc())
        )

        if cursor:
            cursor_dt, cursor_id = decode_cursor(cursor)
            q = q.where(
                or_(
                    OrganizationEvent.occurred_at < cursor_dt,
                    (OrganizationEvent.occurred_at == cursor_dt)
                    & (OrganizationEvent.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        next_cursor = (
            encode_cursor(items[-1].occurred_at, items[-1].id)
            if has_more and items
            else None
        )
        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor
        )
