"""Health endpoint smoke tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "service" in data


@pytest.mark.asyncio
async def test_ready(client: AsyncClient) -> None:
    r = await client.get("/ready")
    # 200 (all deps up) or 503 (degraded — expected in test env without Redis)
    assert r.status_code in (200, 503)
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "dependencies" in data
