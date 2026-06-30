"""Shared fixtures for the API Gateway test suite."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.infrastructure.messaging.publisher import NullPublisher
from app.main import app
from app.services.cache_service import CacheService
from app.services.route_service import RouteService


# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def cache_service(fake_redis: FakeRedis) -> CacheService:
    return CacheService(fake_redis)


@pytest.fixture
def null_publisher() -> NullPublisher:
    return NullPublisher()


@pytest.fixture
def route_service() -> RouteService:
    return RouteService()


# ---------------------------------------------------------------------------
# App client — Redis/RabbitMQ/httpx are all mocked via app.state overrides
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(fake_redis: FakeRedis) -> AsyncClient:
    """ASGI test client with fake Redis injected and RabbitMQ/HTTP client mocked."""
    app.state.redis = fake_redis
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient()  # unused in unit tests; overridden per test

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]

    # Clean up
    app.state.redis = None
    app.state.http_client = None
