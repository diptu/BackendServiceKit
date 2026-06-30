"""Unit tests for health and readiness endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    app.state.redis = None
    app.state.rabbitmq_connection = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]


async def test_health_returns_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_when_infra_unavailable_returns_503(client: AsyncClient) -> None:
    """With no Redis or RabbitMQ the gateway is degraded, not ready."""
    resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["redis"] == "unavailable"
    assert body["rabbitmq"] == "unavailable"


async def test_ready_with_fake_redis_and_no_rabbitmq(client: AsyncClient) -> None:
    """Partial readiness: Redis ok, RabbitMQ down → still degraded."""
    from fakeredis.aioredis import FakeRedis

    app.state.redis = FakeRedis()
    resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["redis"] == "ok"
    assert body["rabbitmq"] == "unavailable"
