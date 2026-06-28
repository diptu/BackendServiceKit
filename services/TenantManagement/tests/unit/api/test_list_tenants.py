"""API-level tests for GET /api/v1/tenants."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app
from app.models import Tenant, TenantContact, TenantMetadata, TenantSettings  # noqa: F401

# ---------------------------------------------------------------------------
# Test DB wiring
# ---------------------------------------------------------------------------

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _SESSION_FACTORY() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "/api/v1/tenants"
_OWNER = str(uuid4())


async def _create(
    client: AsyncClient, name: str, region: str = "us-east-1"
) -> dict[str, Any]:
    resp = await client.post(
        _BASE,
        json={
            "name": name,
            "display_name": name.replace("-", " ").title(),
            "owner_id": _OWNER,
            "region": region,
            "timezone": "UTC",
            "locale": "en-US",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


# ---------------------------------------------------------------------------
# Empty list
# ---------------------------------------------------------------------------


async def test_list_empty(client: AsyncClient) -> None:
    resp = await client.get(_BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["has_more"] is False
    assert body["next_cursor"] is None


# ---------------------------------------------------------------------------
# Basic listing
# ---------------------------------------------------------------------------


async def test_list_returns_created_tenant(client: AsyncClient) -> None:
    await _create(client, "acme-corp")
    resp = await client.get(_BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "acme-corp"


async def test_list_response_shape(client: AsyncClient) -> None:
    await _create(client, "acme-corp")
    body = (await client.get(_BASE)).json()
    item = body["items"][0]
    for key in ("id", "name", "display_name", "status", "region", "created_at"):
        assert key in item, f"missing key: {key}"


async def test_list_multiple_tenants(client: AsyncClient) -> None:
    await _create(client, "alpha-co")
    await _create(client, "beta-co")
    body = (await client.get(_BASE)).json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


async def test_list_limit(client: AsyncClient) -> None:
    await _create(client, "alpha-co")
    await _create(client, "beta-co")
    await _create(client, "gamma-co")
    resp = await client.get(_BASE, params={"limit": 2})
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["has_more"] is True
    assert body["next_cursor"] is not None


async def test_list_cursor_next_page(client: AsyncClient) -> None:
    for i in range(3):
        await _create(client, f"tenant-{i:02d}")
    first = (await client.get(_BASE, params={"limit": 2})).json()
    assert first["has_more"] is True
    second = (
        await client.get(
            _BASE, params={"limit": 2, "next_cursor": first["next_cursor"]}
        )
    ).json()
    assert len(second["items"]) == 1
    assert second["has_more"] is False
    # No overlap between pages
    first_ids = {t["id"] for t in first["items"]}
    second_ids = {t["id"] for t in second["items"]}
    assert first_ids.isdisjoint(second_ids)


async def test_list_limit_min_validation(client: AsyncClient) -> None:
    resp = await client.get(_BASE, params={"limit": 0})
    assert resp.status_code == 422


async def test_list_limit_max_validation(client: AsyncClient) -> None:
    resp = await client.get(_BASE, params={"limit": 101})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Status filter
# ---------------------------------------------------------------------------


async def test_list_filter_status_active(client: AsyncClient) -> None:
    await _create(client, "acme-corp")
    # draft status — should NOT appear in active filter
    resp = await client.get(_BASE, params={"status": "active"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_list_filter_status_draft(client: AsyncClient) -> None:
    await _create(client, "acme-corp")
    resp = await client.get(_BASE, params={"status": "draft"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_filter_status_invalid(client: AsyncClient) -> None:
    resp = await client.get(_BASE, params={"status": "not-a-status"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Region filter
# ---------------------------------------------------------------------------


async def test_list_filter_region(client: AsyncClient) -> None:
    await _create(client, "us-tenant", region="us-east-1")
    await _create(client, "eu-tenant", region="eu-west-1")
    resp = await client.get(_BASE, params={"region": "us-east-1"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "us-tenant"


async def test_list_filter_region_no_match(client: AsyncClient) -> None:
    await _create(client, "us-tenant", region="us-east-1")
    resp = await client.get(_BASE, params={"region": "ap-southeast-1"})
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Search filter
# ---------------------------------------------------------------------------


async def test_list_search_by_name(client: AsyncClient) -> None:
    await _create(client, "acme-corp")
    await _create(client, "beta-co")
    resp = await client.get(_BASE, params={"search": "acme"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "acme-corp"


async def test_list_search_no_match(client: AsyncClient) -> None:
    await _create(client, "acme-corp")
    resp = await client.get(_BASE, params={"search": "zzz"})
    assert resp.json()["total"] == 0


async def test_list_search_too_long(client: AsyncClient) -> None:
    resp = await client.get(_BASE, params={"search": "x" * 101})
    assert resp.status_code == 422
