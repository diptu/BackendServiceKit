"""Health endpoint tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_all_ok(client: AsyncClient, mocker: object) -> None:
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.database.session.SessionLocal",
        _FakeSession(),
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.get_redis",
        return_value=_FakeRedis(),
    )
    mocker.patch(  # type: ignore[attr-defined]
        "aio_pika.connect",
        return_value=_FakeAMQPConn(),
    )
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
    assert body["checks"]["rabbitmq"] == "ok"


async def test_ready_503_when_db_fails(client: AsyncClient, mocker: object) -> None:
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.database.session.SessionLocal",
        _BrokenSession(),
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.get_redis",
        return_value=_FakeRedis(),
    )
    mocker.patch(  # type: ignore[attr-defined]
        "aio_pika.connect",
        return_value=_FakeAMQPConn(),
    )
    resp = await client.get("/ready")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["checks"]["database"].startswith("error:")
    assert detail["checks"]["redis"] == "ok"


async def test_metrics_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert b"provisioning_jobs_started_total" in resp.content


# ── helpers ──────────────────────────────────────────────────────────────────


class _FakeSession:
    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def execute(self, *_: object) -> None:
        pass

    def __call__(self) -> "_FakeSession":
        return self


class _BrokenSession:
    async def __aenter__(self) -> "_BrokenSession":
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def execute(self, *_: object) -> None:
        raise RuntimeError("db_down")

    def __call__(self) -> "_BrokenSession":
        return self


class _FakeRedis:
    async def ping(self) -> bool:
        return True

    def __call__(self) -> "_FakeRedis":
        return self


class _FakeAMQPConn:
    async def close(self) -> None:
        pass
