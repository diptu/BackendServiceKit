"""Repository for AuditEvent — record + paginated queries."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, or_, select

from app.models.audit_event import AuditEvent
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class AuditEventRepository(BaseRepository[AuditEvent]):
    async def record(
        self,
        *,
        tenant_id: uuid.UUID,
        event_type: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        subject_user_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        details: dict[str, object] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            subject_user_id=subject_user_id,
            actor_id=actor_id,
            details=details,
        )
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        subject_user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AuditEvent]:
        base_where = [AuditEvent.tenant_id == tenant_id]
        if subject_user_id is not None:
            base_where.append(AuditEvent.subject_user_id == subject_user_id)
        if resource_type is not None:
            base_where.append(AuditEvent.resource_type == resource_type)

        total_result = await self._session.execute(
            select(func.count()).select_from(AuditEvent).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(AuditEvent)
            .where(*base_where)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        )

        if cursor:
            cursor_dt, cursor_id = decode_cursor(cursor)
            q = q.where(
                or_(
                    AuditEvent.occurred_at < cursor_dt,
                    and_(
                        AuditEvent.occurred_at == cursor_dt, AuditEvent.id < cursor_id
                    ),
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
