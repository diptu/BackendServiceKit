"""
Access-token revocation store.

Two distinct revocation needs, one backend:

  - Logout revokes exactly one token the caller is holding right now — a
    point lookup by jti (`add_jti`/`contains_jti`), mirroring the existing
    jti-keyed `ACTIVE_REFRESH_TOKENS` pattern on `app.models.user`.
  - A password change/reset must invalidate *every* access token the user
    currently holds across however many devices/sessions, without tracking
    every jti ever issued. Comparing the token's `iat` claim against a
    single per-user `invalidate_before` timestamp (`set_invalidate_before`/
    `get_invalidate_before`) gets the same effect in O(1) with no extra
    bookkeeping at issuance time.

`password_changed_at` on the `User` row (see the account-lockout migration)
is the durable source of truth for the invalidation horizon; the entry
here is a hot-path-fast mirror seeded at change time so the auth dependency
never needs a DB round trip to check it. If this cache entry is lost (e.g.
process restart with the in-memory backend) but the DB column is set, a
token issued before the change won't be rejected until the cache is
repopulated — bounded by the access token's own short lifetime, an
accepted trade-off for the $0-cost in-memory default.

Mirrors the Protocol + InMemory + Redis + lazy-singleton-with-fallback
shape of `app.core.cache` / `app.core.rate_limit`.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from app.core.config import settings

_JTI_PREFIX = "blacklist:jti:"
_INVALIDATE_BEFORE_PREFIX = "blacklist:invalidate_before:"


class TokenBlacklist(Protocol):
    async def add_jti(self, jti: str, ttl_seconds: int) -> None: ...

    async def contains_jti(self, jti: str) -> bool: ...

    async def set_invalidate_before(
        self, user_id: str, timestamp: float, ttl_seconds: int
    ) -> None: ...

    async def get_invalidate_before(self, user_id: str) -> float | None: ...


class InMemoryTokenBlacklist:
    """Process-local revocation store."""

    def __init__(self) -> None:
        self._jtis: dict[str, float] = {}  # jti -> expires_at (monotonic)
        self._invalidate_before: dict[str, tuple[float, float]] = {}
        # user_id -> (timestamp, expires_at)

    async def add_jti(self, jti: str, ttl_seconds: int) -> None:
        self._jtis[jti] = time.monotonic() + ttl_seconds

    async def contains_jti(self, jti: str) -> bool:
        expires_at = self._jtis.get(jti)
        if expires_at is None:
            return False
        if expires_at < time.monotonic():
            del self._jtis[jti]
            return False
        return True

    async def set_invalidate_before(
        self, user_id: str, timestamp: float, ttl_seconds: int
    ) -> None:
        self._invalidate_before[user_id] = (timestamp, time.monotonic() + ttl_seconds)

    async def get_invalidate_before(self, user_id: str) -> float | None:
        entry = self._invalidate_before.get(user_id)
        if entry is None:
            return None
        timestamp, expires_at = entry
        if expires_at < time.monotonic():
            del self._invalidate_before[user_id]
            return None
        return timestamp

    def clear(self) -> None:
        """Test helper — wipe all entries."""
        self._jtis.clear()
        self._invalidate_before.clear()


class RedisTokenBlacklist:
    """Redis-backed revocation store for multi-replica deployments."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis  # local import: optional dependency

        self._client = redis.from_url(redis_url, decode_responses=True)

    async def add_jti(self, jti: str, ttl_seconds: int) -> None:
        await self._client.set(f"{_JTI_PREFIX}{jti}", "1", ex=max(ttl_seconds, 1))

    async def contains_jti(self, jti: str) -> bool:
        return bool(await self._client.exists(f"{_JTI_PREFIX}{jti}"))

    async def set_invalidate_before(
        self, user_id: str, timestamp: float, ttl_seconds: int
    ) -> None:
        await self._client.set(
            f"{_INVALIDATE_BEFORE_PREFIX}{user_id}",
            str(timestamp),
            ex=max(ttl_seconds, 1),
        )

    async def get_invalidate_before(self, user_id: str) -> float | None:
        raw = await self._client.get(f"{_INVALIDATE_BEFORE_PREFIX}{user_id}")
        if raw is None:
            return None
        return float(raw)


_blacklist: TokenBlacklist | None = None


def get_token_blacklist() -> TokenBlacklist:
    """
    Lazily build the process-wide token revocation store.

    Production: set REDIS_URL to share revocations across replicas.
    Dev/tests fall back to an in-memory store automatically — and fall
    back again, silently, if constructing the Redis client fails for any
    reason, so a misconfigured store degrades to "nothing is revoked"
    rather than crashing the request path.
    """
    global _blacklist
    if _blacklist is None:
        if settings.REDIS_URL:
            try:
                _blacklist = RedisTokenBlacklist(settings.REDIS_URL)
            except Exception:
                _blacklist = InMemoryTokenBlacklist()
        else:
            _blacklist = InMemoryTokenBlacklist()
    return _blacklist


def reset_token_blacklist() -> None:
    """Test helper: force a fresh store instance on the next call."""
    global _blacklist
    _blacklist = None


async def is_token_revoked(payload: dict[str, Any]) -> bool:
    """
    Shared revocation check for decoded JWT claims, used by both
    `app.middleware.authorization` (at the edge) and
    `app.core.security.is_authenticated` (the dependency fallback) — a
    blacklisted jti (explicit logout) or a token issued before the
    account's last password change/reset must be rejected even though its
    signature and `exp` are still valid.
    """
    blacklist = get_token_blacklist()

    jti = payload.get("jti")
    if jti and await blacklist.contains_jti(jti):
        return True

    sub = payload.get("sub")
    iat = payload.get("iat")
    if sub and iat is not None:
        invalidate_before = await blacklist.get_invalidate_before(sub)
        if invalidate_before is not None and iat < invalidate_before:
            return True

    return False
