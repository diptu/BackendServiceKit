"""Async dependency check functions — Redis, RabbitMQ, PostgreSQL."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from shared.observability.health.readiness import DependencyStatus


async def check_redis(client: Any) -> DependencyStatus:
    """Ping Redis; 2 s timeout."""
    start = time.monotonic()
    try:
        await asyncio.wait_for(client.ping(), timeout=2.0)
        return DependencyStatus(
            name="redis",
            status="up",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as exc:
        return DependencyStatus(name="redis", status="down", error=str(exc))


async def check_rabbitmq(connection: Any | None) -> DependencyStatus:
    """Check RabbitMQ connection state."""
    if connection is None:
        return DependencyStatus(name="rabbitmq", status="down", error="not connected")
    try:
        if getattr(connection, "is_closed", True):
            return DependencyStatus(name="rabbitmq", status="down", error="connection closed")
        return DependencyStatus(name="rabbitmq", status="up", latency_ms=0.0)
    except Exception as exc:
        return DependencyStatus(name="rabbitmq", status="down", error=str(exc))


async def check_postgres(session_maker: Any) -> DependencyStatus:
    """Execute SELECT 1 via SQLAlchemy async session; 2 s timeout."""
    import sqlalchemy

    start = time.monotonic()
    try:
        async with session_maker() as session:
            await asyncio.wait_for(
                session.execute(sqlalchemy.text("SELECT 1")),
                timeout=2.0,
            )
        return DependencyStatus(
            name="postgres",
            status="up",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as exc:
        return DependencyStatus(name="postgres", status="down", error=str(exc))
