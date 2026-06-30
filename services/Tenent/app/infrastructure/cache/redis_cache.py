"""Async Redis cache — fault-tolerant: silently degrades if Redis is unavailable."""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_client: Any = None


def get_redis() -> Any:
    global _client
    if _client is None:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]
        from app.core.config import settings
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def cache_get(key: str) -> dict[str, Any] | None:
    try:
        raw = await get_redis().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("cache_get_failed", extra={"key": key, "error": str(exc)})
        return None


async def cache_get_str(key: str) -> str | None:
    try:
        return await get_redis().get(key)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.debug("cache_get_str_failed", extra={"key": key, "error": str(exc)})
        return None


async def cache_set(key: str, value: dict[str, Any], ttl: int = 60) -> None:
    try:
        await get_redis().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.debug("cache_set_failed", extra={"key": key, "error": str(exc)})


async def cache_set_str(key: str, value: str, ttl: int = 60) -> None:
    try:
        await get_redis().set(key, value, ex=ttl)
    except Exception as exc:
        logger.debug("cache_set_str_failed", extra={"key": key, "error": str(exc)})


async def cache_delete(key: str) -> None:
    try:
        await get_redis().delete(key)
    except Exception as exc:
        logger.debug("cache_delete_failed", extra={"key": key, "error": str(exc)})


async def cache_delete_by_prefix(prefix: str) -> int:
    """Delete all keys matching prefix via SCAN. Returns count deleted."""
    deleted = 0
    try:
        client = get_redis()
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=f"{prefix}*", count=100)
            if keys:
                deleted += await client.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.debug("cache_delete_by_prefix_failed", extra={"prefix": prefix, "error": str(exc)})
    return deleted


def policy_cache_key(tenant_id: str) -> str:
    return f"isolation:policy:{tenant_id}"


def claim_cache_key(resource_type: str, resource_id: str) -> str:
    return f"isolation:claim:{resource_type}:{resource_id}"


def decision_cache_key(
    caller: str, target: str, resource_id: str, resource_type: str, action: str
) -> str:
    return f"isolation:decision:{caller}:{target}:{resource_id}:{resource_type}:{action}"
