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


async def cache_set(key: str, value: dict[str, Any], ttl: int = 60) -> None:
    try:
        await get_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("cache_set_failed", extra={"key": key, "error": str(exc)})


async def cache_delete(key: str) -> None:
    try:
        await get_redis().delete(key)
    except Exception as exc:
        logger.debug("cache_delete_failed", extra={"key": key, "error": str(exc)})


def job_cache_key(job_id: str) -> str:
    return f"provisioning:job:{job_id}"
