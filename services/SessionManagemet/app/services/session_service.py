"""SessionService — session lifecycle, tracking, and revocation.

Session tokens are opaque random strings (secrets.token_urlsafe), hashed at
rest (SHA-256) and never stored raw — the same pattern Authentication uses for
refresh tokens. The raw token is returned once, at creation, and is what
`/sessions/me` and refresh are looked up by.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.commands import CreateSessionCmd
from app.domain.enums import SessionStatus
from app.domain.exceptions import InvalidSessionTokenError, SessionNotFoundError
from app.models.session import Session
from app.repositories.base import PageResult
from app.repositories.session import SessionRepository


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on DateTime(timezone=True) columns; treat a naive
    value read back from the DB as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def session_status(session: Session, *, now: datetime | None = None) -> SessionStatus:
    now = now or datetime.now(timezone.utc)
    if session.revoked_at is not None:
        return SessionStatus.REVOKED
    if _as_aware_utc(session.expires_at) <= now:
        return SessionStatus.EXPIRED
    return SessionStatus.ACTIVE


class CreatedSession:
    __slots__ = ("session", "raw_token")

    def __init__(self, session: Session, raw_token: str) -> None:
        self.session = session
        self.raw_token = raw_token


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = SessionRepository(db)

    async def create(
        self, tenant_id: uuid.UUID, cmd: CreateSessionCmd
    ) -> CreatedSession:
        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        ttl = cmd.ttl_seconds or settings.session_ttl_seconds
        session = await self._repo.create(
            Session(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=cmd.user_id,
                token_hash=_hash_token(raw_token),
                device_info=cmd.device_info,
                ip_address=cmd.ip_address,
                user_agent=cmd.user_agent,
                created_at=now,
                last_seen_at=now,
                expires_at=now + timedelta(seconds=ttl),
            )
        )
        return CreatedSession(session, raw_token)

    async def get(self, tenant_id: uuid.UUID, session_id: uuid.UUID) -> Session:
        session = await self._repo.get_by_id(session_id, tenant_id=tenant_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        active_only: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Session]:
        return await self._repo.list(
            tenant_id=tenant_id,
            user_id=user_id,
            active_only=active_only,
            cursor=cursor,
            limit=limit,
        )

    async def resolve_by_token(self, tenant_id: uuid.UUID, raw_token: str) -> Session:
        session = await self._repo.get_by_token_hash(
            _hash_token(raw_token), tenant_id=tenant_id
        )
        if session is None or session_status(session) is not SessionStatus.ACTIVE:
            raise InvalidSessionTokenError()
        return session

    async def refresh(self, tenant_id: uuid.UUID, session_id: uuid.UUID) -> Session:
        """Extend an active session's lifetime and bump last_seen. A revoked or
        expired session cannot be refreshed (treated as not found)."""
        session = await self.get(tenant_id, session_id)
        if session_status(session) is not SessionStatus.ACTIVE:
            raise SessionNotFoundError(session_id)
        now = datetime.now(timezone.utc)
        session.last_seen_at = now
        session.expires_at = now + timedelta(
            seconds=settings.session_refresh_extends_seconds
        )
        return await self._repo.save(session)

    async def revoke(self, tenant_id: uuid.UUID, session_id: uuid.UUID) -> None:
        # Idempotent — revoking an unknown/already-revoked session is a no-op,
        # not a 404 that would leak whether the session exists.
        await self._repo.revoke(session_id, tenant_id=tenant_id)

    async def revoke_all_for_user(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        return await self._repo.revoke_all_for_user(user_id, tenant_id=tenant_id)
