from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.core.config import settings


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@respx.mock
async def test_ready_when_prometheus_up(client: AsyncClient) -> None:
    respx.get(f"{settings.prometheus_base_url}/-/ready").mock(return_value=Response(200))
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "prometheus": True}


@respx.mock
async def test_ready_when_prometheus_down(client: AsyncClient) -> None:
    respx.get(f"{settings.prometheus_base_url}/-/ready").mock(return_value=Response(503))
    resp = await client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["prometheus"] is False
