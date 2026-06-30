"""Redis auto-instrumentation — creates spans for every Redis command."""

from __future__ import annotations


def instrument_redis() -> None:
    """Instrument the redis-py client to emit OTel spans for cache operations."""
    from opentelemetry.instrumentation.redis import RedisInstrumentor  # type: ignore[import]

    RedisInstrumentor().instrument()
