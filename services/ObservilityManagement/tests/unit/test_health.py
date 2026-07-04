from __future__ import annotations

from httpx import AsyncClient

from app.core.config import settings


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == settings.app_name


async def test_ready(client: AsyncClient) -> None:
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
