"""API-level tests for GET /api/v1/tenants/{tenant_id}."""

from __future__ import annotations

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


async def _override_get_db() -> AsyncSession:
    async with _SESSION_FACTORY() as session:
        try:
            yield session  # type: ignore[misc]
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # type: ignore[misc]
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "/api/v1/tenants"
_OWNER = str(uuid4())


async def _create(client: AsyncClient, name: str = "acme-corp") -> dict:
    resp = await client.post(
        _BASE,
        json={
            "name": name,
            "display_name": name.replace("-", " ").title(),
            "owner_id": _OWNER,
            "region": "us-east-1",
            "timezone": "UTC",
            "locale": "en-US",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_get_returns_tenant(client: AsyncClient) -> None:
    created = await _create(client)
    resp = await client.get(f"{_BASE}/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_response_matches_create(client: AsyncClient) -> None:
    created = await _create(client)
    fetched = (await client.get(f"{_BASE}/{created['id']}")).json()
    for field in ("id", "name", "display_name", "status", "region", "owner_id"):
        assert fetched[field] == created[field], f"field {field!r} mismatch"


async def test_get_response_shape(client: AsyncClient) -> None:
    created = await _create(client)
    body = (await client.get(f"{_BASE}/{created['id']}")).json()
    for key in (
        "id", "name", "display_name", "description",
        "status", "region", "timezone", "locale", "currency",
        "owner_id", "created_at", "updated_at", "deleted_at",
    ):
        assert key in body, f"missing key: {key!r}"


async def test_get_description_null_when_not_provided(client: AsyncClient) -> None:
    created = await _create(client)
    body = (await client.get(f"{_BASE}/{created['id']}")).json()
    assert body["description"] is None


async def test_get_deleted_at_null_for_active_tenant(client: AsyncClient) -> None:
    created = await _create(client)
    body = (await client.get(f"{_BASE}/{created['id']}")).json()
    assert body["deleted_at"] is None


async def test_get_status_is_draft_on_creation(client: AsyncClient) -> None:
    created = await _create(client)
    body = (await client.get(f"{_BASE}/{created['id']}")).json()
    assert body["status"] == "draft"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


async def test_get_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/{uuid4()}")
    assert resp.status_code == 404


async def test_get_invalid_uuid_returns_422(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/not-a-uuid")
    assert resp.status_code == 422


async def test_get_soft_deleted_tenant_returns_404(client: AsyncClient) -> None:
    created = await _create(client)
    tid = created["id"]
    # Force to archived then delete
    async with _SESSION_FACTORY() as s:
        await s.execute(update(Tenant).where(Tenant.id == UUID(tid)).values(status="archived"))
        await s.commit()
    del_resp = await client.delete(f"{_BASE}/{tid}")
    assert del_resp.status_code == 204

    resp = await client.get(f"{_BASE}/{tid}")
    assert resp.status_code == 404
