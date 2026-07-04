from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from app.core.config import settings


@pytest.fixture(autouse=True)
def _disable_jwt() -> None:
    settings.jwt_auth_enabled = False


@respx.mock
async def test_logs_search_accessible_when_jwt_auth_disabled(client: AsyncClient) -> None:
    respx.get(f"{settings.loki_base_url}/loki/api/v1/query_range").mock(
        return_value=Response(200, json={"data": {"result": []}})
    )
    resp = await client.get("/api/v1/logs/search")
    assert resp.status_code == 200


async def test_logs_search_requires_bearer_token_when_jwt_auth_enabled(client: AsyncClient) -> None:
    settings.jwt_auth_enabled = True
    try:
        resp = await client.get("/api/v1/logs/search")
        assert resp.status_code == 401
    finally:
        settings.jwt_auth_enabled = False
