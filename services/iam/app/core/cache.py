"""
ACL (permission-vector) cache abstraction.

Org-scoped permission sets can't ride in the JWT (they change without a
re-login, and a user may belong to many orgs), so they're the one
authorization path that needs a cache-aside lookup. This module provides:

  - InMemoryPermissionCache: zero-dependency default — correct for a single
    process and exactly what tests exercise (no Redis server to provision).
  - RedisPermissionCache: opt-in, for sharing the cache across replicas in
    production. `redis` is imported lazily so it stays an optional
    dependency; if it's missing or REDIS_URL is unreachable, the process
    transparently falls back to the in-memory cache.

Either backend is reached exclusively through `get_permission_cache()`.
"""

from __future__ import annotations

import time
from typing import Protocol

from app.core.config import settings


class PermissionCache(Protocol):
    async def get(self, key: str) -> set[str] | None: ...

    async def set(self, key: str, value: set[str], ttl_seconds: int) -> None: ...


class InMemoryPermissionCache:
    """Process-local cache-aside store."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, set[str]]] = {}

    async def get(self, key: str) -> set[str] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: set[str], ttl_seconds: int) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, set(value))

    def clear(self) -> None:
        """Test helper — wipe all entries."""
        self._store.clear()


class RedisPermissionCache:
    """Redis-backed ACL cache for multi-replica deployments."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis  # local import: optional dependency

        self._client = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> set[str] | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        text = raw.decode() if isinstance(raw, bytes) else raw
        return set(text.split(",")) if text else set()

    async def set(self, key: str, value: set[str], ttl_seconds: int) -> None:
        await self._client.set(key, ",".join(sorted(value)), ex=ttl_seconds)


_cache: PermissionCache | None = None


def get_permission_cache() -> PermissionCache:
    """
    Lazily build the process-wide permission cache.

    Production: set REDIS_URL to share the cache across replicas. Dev/tests
    ($0 cost, no infra to provision) fall back to an in-memory cache
    automatically — and fall back again, silently, if constructing the
    Redis client fails for any reason (missing package, bad URL, etc.), so a
    misconfigured cache degrades to "always recompute" rather than crashing
    the request path.
    """
    global _cache
    if _cache is None:
        if settings.REDIS_URL:
            try:
                _cache = RedisPermissionCache(settings.REDIS_URL)
            except Exception:
                # Best-effort cache: any construction failure (missing
                # package, bad URL, ...) degrades to in-memory rather than
                # crashing the request path.
                _cache = InMemoryPermissionCache()
        else:
            _cache = InMemoryPermissionCache()
    return _cache


def reset_permission_cache() -> None:
    """Test helper: force a fresh cache instance on the next call."""
    global _cache
    _cache = None
