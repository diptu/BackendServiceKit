"""API-level tests for PATCH /api/v1/tenants/{tenant_id}."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
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


async def _create(client: AsyncClient, name: str = "acme-corp") -> dict[str, Any]:
    resp = await client.post(
        _BASE,
        json={
            "name": name,
            "display_name": "Acme Corp",
            "description": "Original description.",
            "owner_id": _OWNER,
            "region": "us-east-1",
            "timezone": "UTC",
            "locale": "en-US",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


async def _force_status(tenant_id: str, status: str) -> None:
    async with _SESSION_FACTORY() as s:
        await s.execute(
            update(Tenant).where(Tenant.id == UUID(tenant_id)).values(status=status)
        )
        await s.commit()


# ---------------------------------------------------------------------------
# Happy path — individual fields
# ---------------------------------------------------------------------------


async def test_update_display_name(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(
        f"{_BASE}/{tid}", json={"display_name": "Acme Corp (Updated)"}
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Acme Corp (Updated)"


async def test_update_description(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(
        f"{_BASE}/{tid}", json={"description": "New description."}
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "New description."


async def test_update_region(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"region": "eu-west-1"})
    assert resp.status_code == 200
    assert resp.json()["region"] == "eu-west-1"


async def test_update_timezone(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"timezone": "Europe/London"})
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "Europe/London"


async def test_update_locale(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"locale": "en-GB"})
    assert resp.status_code == 200
    assert resp.json()["locale"] == "en-GB"


async def test_update_currency(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"currency": "GBP"})
    assert resp.status_code == 200
    assert resp.json()["currency"] == "GBP"


async def test_update_multiple_fields(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(
        f"{_BASE}/{tid}",
        json={
            "display_name": "New Name",
            "region": "ap-southeast-1",
            "currency": "SGD",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "New Name"
    assert body["region"] == "ap-southeast-1"
    assert body["currency"] == "SGD"


# ---------------------------------------------------------------------------
# No-op and immutability
# ---------------------------------------------------------------------------


async def test_update_empty_body_is_noop(client: AsyncClient) -> None:
    created = await _create(client)
    resp = await client.patch(f"{_BASE}/{created['id']}", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == created["display_name"]
    assert body["region"] == created["region"]


async def test_update_does_not_change_name(client: AsyncClient) -> None:
    """name (slug) is immutable — passing it in the body should not change it."""
    created = await _create(client)
    resp = await client.patch(
        f"{_BASE}/{created['id']}", json={"display_name": "Changed"}
    )
    assert resp.json()["name"] == "acme-corp"


async def test_update_does_not_change_id(client: AsyncClient) -> None:
    created = await _create(client)
    resp = await client.patch(
        f"{_BASE}/{created['id']}", json={"display_name": "Changed"}
    )
    assert resp.json()["id"] == created["id"]


async def test_update_does_not_change_created_at(client: AsyncClient) -> None:
    created = await _create(client)
    resp = await client.patch(
        f"{_BASE}/{created['id']}", json={"display_name": "Changed"}
    )
    assert resp.json()["created_at"] == created["created_at"]


# ---------------------------------------------------------------------------
# Validation errors (422)
# ---------------------------------------------------------------------------


async def test_update_display_name_empty_string_returns_422(
    client: AsyncClient,
) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"display_name": ""})
    assert resp.status_code == 422


async def test_update_display_name_too_long_returns_422(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"display_name": "x" * 256})
    assert resp.status_code == 422


async def test_update_region_too_short_returns_422(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.patch(f"{_BASE}/{tid}", json={"region": "a"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Domain error cases
# ---------------------------------------------------------------------------


async def test_update_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.patch(f"{_BASE}/{uuid4()}", json={"display_name": "Ghost"})
    assert resp.status_code == 404


async def test_update_archived_tenant_returns_423(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "archived")
    resp = await client.patch(f"{_BASE}/{tid}", json={"display_name": "Blocked"})
    assert resp.status_code == 423


async def test_update_invalid_uuid_returns_422(client: AsyncClient) -> None:
    resp = await client.patch(f"{_BASE}/not-a-uuid", json={"display_name": "X"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


async def test_update_response_shape(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    body = (
        await client.patch(f"{_BASE}/{tid}", json={"display_name": "Changed"})
    ).json()
    for key in (
        "id",
        "name",
        "display_name",
        "description",
        "status",
        "region",
        "timezone",
        "locale",
        "currency",
        "owner_id",
        "created_at",
        "updated_at",
        "deleted_at",
    ):
        assert key in body, f"missing key: {key!r}"
