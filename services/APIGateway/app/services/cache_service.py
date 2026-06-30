"""Cache service — Redis-backed response caching with TTL and invalidation."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.constants import CACHE_KEY_PREFIX
from app.domain.enums import CacheResult

logger = logging.getLogger(__name__)

# Type alias — avoid importing redis at module level so tests can inject fakeredis
_RedisClient = Any


class CacheService:
    """Wraps async Redis operations with gateway-specific key strategy.

    Cache key format:
        gw:{upstream}:{path_hash}
    where path_hash = sha256("{path}?{sorted_query_string}")[:16]

    Tenant-scoped invalidation pattern:
        gw:{upstream}:{tenant_id}:* (matched via SCAN)
    """

    def __init__(self, redis: _RedisClient | None) -> None:
        self._redis = redis

    @property
    def available(self) -> bool:
        return self._redis is not None

    # ------------------------------------------------------------------
    # Key builders
    # ------------------------------------------------------------------

    @staticmethod
    def build_key(upstream: str, path: str, query_string: str = "") -> str:
        raw = f"{path}?{query_string}" if query_string else path
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"{CACHE_KEY_PREFIX}:{upstream}:{digest}"

    @staticmethod
    def tenant_pattern(upstream: str, tenant_id: str) -> str:
        """Glob pattern matching all cache keys for a specific tenant under an upstream."""
        # Keys that contain the tenant_id in the path are indexed separately via a set.
        # We use a secondary set key to track which cache keys belong to a tenant.
        return f"{CACHE_KEY_PREFIX}:{upstream}:tenant:{tenant_id}"

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> tuple[bytes | None, CacheResult]:
        if self._redis is None:
            return None, CacheResult.ERROR
        try:
            value: bytes | None = await self._redis.get(key)
            return value, CacheResult.HIT if value is not None else CacheResult.MISS
        except Exception as exc:
            logger.warning("cache_get_error", extra={"key": key, "error": str(exc)})
            return None, CacheResult.ERROR

    async def set(
        self,
        key: str,
        value: bytes,
        ttl: int,
        *,
        tenant_id: str | None = None,
        upstream: str = "",
    ) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.setex(key, ttl, value)
            if tenant_id and upstream:
                # Track this cache key under the tenant's index set (TTL = cache TTL + buffer)
                index_key = self.tenant_pattern(upstream, tenant_id)
                await self._redis.sadd(index_key, key)
                await self._redis.expire(index_key, ttl + 60)
        except Exception as exc:
            logger.warning("cache_set_error", extra={"key": key, "error": str(exc)})

    async def invalidate_tenant(self, tenant_id: str, upstream: str) -> int:
        """Delete all cached responses for a tenant under a specific upstream.

        Returns the number of keys deleted.
        """
        if self._redis is None:
            return 0
        try:
            index_key = self.tenant_pattern(upstream, tenant_id)
            members: set[bytes] = await self._redis.smembers(index_key)
            if not members:
                return 0
            pipe = self._redis.pipeline()
            for member in members:
                pipe.delete(member)
            pipe.delete(index_key)
            results = await pipe.execute()
            deleted = sum(1 for r in results[:-1] if r)
            logger.info(
                "cache_invalidated",
                extra={
                    "tenant_id": tenant_id,
                    "upstream": upstream,
                    "keys_deleted": deleted,
                },
            )
            return deleted
        except Exception as exc:
            logger.warning(
                "cache_invalidate_error",
                extra={"tenant_id": tenant_id, "upstream": upstream, "error": str(exc)},
            )
            return 0

    async def invalidate_all_upstreams(self, tenant_id: str, upstream_names: list[str]) -> int:
        """Invalidate tenant cache across all registered upstreams."""
        total = 0
        for upstream in upstream_names:
            total += await self.invalidate_tenant(tenant_id, upstream)
        return total

    async def ping(self) -> bool:
        if self._redis is None:
            return False
        try:
            return await self._redis.ping()  # type: ignore[no-any-return]
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Cached response serialization
    # ------------------------------------------------------------------

    @staticmethod
    def encode_response(status_code: int, headers: dict[str, str], body: bytes) -> bytes:
        envelope = {
            "status_code": status_code,
            "headers": headers,
        }
        prefix = json.dumps(envelope).encode() + b"\x00"
        return prefix + body

    @staticmethod
    def decode_response(raw: bytes) -> tuple[int, dict[str, str], bytes]:
        sep = raw.index(b"\x00")
        envelope = json.loads(raw[:sep])
        body = raw[sep + 1 :]
        return envelope["status_code"], envelope["headers"], body
