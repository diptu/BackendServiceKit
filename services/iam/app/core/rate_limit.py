"""
Fixed-window rate limiter.

A fixed-window counter (not a sorted-set sliding window) is the right
trade-off for a brute-force guard on login: O(1) per request, trivially
mirrored in-memory, and deterministic under a `time.monotonic` monkeypatch
in tests — a true sliding window adds O(log n) state for boundary precision
this threat model doesn't need.

Mirrors the Protocol + InMemory + Redis + lazy-singleton-with-fallback shape
of `app.core.cache` so the same operational story (in-memory by default,
opt into Redis via REDIS_URL to share limits across replicas, degrade to
in-memory on any Redis failure rather than crash the request path) applies
here too.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings


@dataclass(slots=True, frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def hit(
        self, key: str, *, limit: int, window_seconds: int
    ) -> RateLimitResult: ...


class InMemoryRateLimiter:
    """Process-local fixed-window counter."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[int, int]] = {}  # key -> (bucket, count)

    async def hit(
        self, key: str, *, limit: int, window_seconds: int
    ) -> RateLimitResult:
        bucket = int(time.monotonic() // window_seconds)
        stored_bucket, count = self._store.get(key, (bucket, 0))
        if stored_bucket != bucket:
            count = 0
        count += 1
        self._store[key] = (bucket, count)

        if count > limit:
            window_end = (bucket + 1) * window_seconds
            retry_after = max(int(window_end - time.monotonic()), 1)
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
        return RateLimitResult(allowed=True, retry_after_seconds=0)

    def clear(self) -> None:
        """Test helper — wipe all entries."""
        self._store.clear()


class RedisRateLimiter:
    """Redis-backed fixed-window counter for multi-replica deployments."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis  # local import: optional dependency

        self._client = redis.from_url(redis_url, decode_responses=True)

    async def hit(
        self, key: str, *, limit: int, window_seconds: int
    ) -> RateLimitResult:
        bucket = int(time.time() // window_seconds)
        redis_key = f"ratelimit:{key}:{bucket}"

        count = await self._client.incr(redis_key)
        if count == 1:
            await self._client.expire(redis_key, window_seconds)

        if count > limit:
            window_end = (bucket + 1) * window_seconds
            retry_after = max(int(window_end - time.time()), 1)
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
        return RateLimitResult(allowed=True, retry_after_seconds=0)


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """
    Lazily build the process-wide rate limiter.

    Production: set REDIS_URL to share limits across replicas. Dev/tests
    ($0 cost, no infra to provision) fall back to an in-memory limiter
    automatically — and fall back again, silently, if constructing the
    Redis client fails for any reason, so a misconfigured limiter degrades
    to "always allow" rather than crashing the request path.
    """
    global _limiter
    if _limiter is None:
        if settings.REDIS_URL:
            try:
                _limiter = RedisRateLimiter(settings.REDIS_URL)
            except Exception:
                _limiter = InMemoryRateLimiter()
        else:
            _limiter = InMemoryRateLimiter()
    return _limiter


def reset_rate_limiter() -> None:
    """Test helper: force a fresh limiter instance on the next call."""
    global _limiter
    _limiter = None
