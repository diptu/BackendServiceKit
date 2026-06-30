"""Async Redis client factory and FastAPI dependency."""

from __future__ import annotations

import logging

from fastapi import Request
from redis.asyncio import Redis
from redis.asyncio.client import Redis as AsyncRedis

from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_redis_client() -> AsyncRedis:  # type: ignore[type-arg]
    """Create and return a connected async Redis client."""
    client: AsyncRedis = Redis.from_url(  # type: ignore[type-arg]
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False,  # raw bytes — we handle encoding in CacheService
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )
    return client


async def close_redis_client(client: AsyncRedis) -> None:  # type: ignore[type-arg]
    await client.aclose()


def get_redis(request: Request) -> AsyncRedis | None:  # type: ignore[type-arg]
    """FastAPI dependency: returns the shared Redis client or None when unavailable."""
    return getattr(request.app.state, "redis", None)  # type: ignore[no-any-return]
