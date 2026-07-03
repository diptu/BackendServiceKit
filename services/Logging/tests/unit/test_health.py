from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.core.config import settings


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@respx.mock
async def test_ready_when_loki_up(client: AsyncClient) -> None:
    respx.get(f"{settings.loki_base_url}/ready").mock(return_value=Response(200))
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "loki": True}


@respx.mock
async def test_ready_when_loki_down(client: AsyncClient) -> None:
    respx.get(f"{settings.loki_base_url}/ready").mock(return_value=Response(500))
    resp = await client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["loki"] is False
