"""SessionRepository — tenant-scoped data access for sessions.

`tenant_id` is a required keyword argument on every lookup — never optional —
so a caller in tenant A can never read or mutate tenant B's sessions, even by
guessing a session UUID. In Siloed mode the session is already bound to the
tenant's own database; this scoping stays as defense-in-depth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, update

from app.models.session import Session
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class SessionRepository(BaseRepository[Session]):
    async def create(self, session: Session) -> Session:
        self._session.add(session)
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def save(self, session: Session) -> Session:
        self._session.add(session)
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def get_by_id(self, session_id: UUID, *, tenant_id: UUID) -> Session | None:
        result = await self._session.execute(
            select(Session).where(
                Session.id == session_id, Session.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token_hash(
        self, token_hash: str, *, tenant_id: UUID
    ) -> Session | None:
        result = await self._session.execute(
            select(Session).where(
                Session.token_hash == token_hash, Session.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None = None,
        active_only: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Session]:
        base: Select[tuple[Session]] = select(Session).where(
            Session.tenant_id == tenant_id
        )
        base = self._apply_filters(base, user_id=user_id, active_only=active_only)

        total = await self._session.scalar(
            select(func.count()).select_from(base.subquery())
        )

        stmt = base
        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Session.created_at < cursor_dt,
                    and_(Session.created_at == cursor_dt, Session.id < cursor_id),
                )
            )
        stmt = stmt.order_by(Session.created_at.desc(), Session.id.desc()).limit(
            limit + 1
        )

        result = await self._session.execute(stmt)
        rows: list[Session] = list(result.scalars())
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        return PageResult(
            items=items,
            total=total or 0,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Session]],
        *,
        user_id: UUID | None,
        active_only: bool,
    ) -> Select[tuple[Session]]:
        if user_id is not None:
            stmt = stmt.where(Session.user_id == user_id)
        if active_only:
            now = datetime.now(timezone.utc)
            stmt = stmt.where(Session.revoked_at.is_(None), Session.expires_at > now)
        return stmt

    async def revoke(self, session_id: UUID, *, tenant_id: UUID) -> None:
        await self._session.execute(
            update(Session)
            .where(
                Session.id == session_id,
                Session.tenant_id == tenant_id,
                Session.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID, *, tenant_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.tenant_id == tenant_id,
                Session.revoked_at.is_(None),
            )
        )
        sessions = list(result.scalars())
        for session in sessions:
            session.revoked_at = now
        await self._session.flush()
        return len(sessions)
