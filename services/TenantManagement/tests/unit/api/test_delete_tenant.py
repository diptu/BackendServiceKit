"""API-level tests for DELETE /api/v1/tenants/{tenant_id}.

The endpoint performs a *soft delete*:
- Requires the tenant to be in `archived` state first.
- Returns 204 No Content on success.
- The soft-deleted tenant is no longer visible via GET or LIST.
- Deleting from any state other than `archived` returns 409.
"""

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


async def _force_status(tenant_id: str, status: str) -> None:
    async with _SESSION_FACTORY() as s:
        await s.execute(
            update(Tenant).where(Tenant.id == UUID(tenant_id)).values(status=status)
        )
        await s.commit()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_delete_archived_tenant_returns_204(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "archived")

    resp = await client.delete(f"{_BASE}/{tid}")
    assert resp.status_code == 204
    assert resp.content == b""


async def test_delete_removes_tenant_from_get(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "archived")
    await client.delete(f"{_BASE}/{tid}")

    resp = await client.get(f"{_BASE}/{tid}")
    assert resp.status_code == 404


async def test_delete_removes_tenant_from_list(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "archived")
    await client.delete(f"{_BASE}/{tid}")

    resp = await client.get(_BASE)
    ids = [t["id"] for t in resp.json()["items"]]
    assert tid not in ids


async def test_delete_does_not_affect_other_tenants(client: AsyncClient) -> None:
    tid1 = (await _create(client, "alpha-co"))["id"]
    tid2 = (await _create(client, "beta-co"))["id"]
    await _force_status(tid1, "archived")
    await client.delete(f"{_BASE}/{tid1}")

    resp = await client.get(f"{_BASE}/{tid2}")
    assert resp.status_code == 200
    assert resp.json()["id"] == tid2


# ---------------------------------------------------------------------------
# Pre-condition failures (409) — must be archived first
# ---------------------------------------------------------------------------


async def test_delete_draft_returns_409(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    resp = await client.delete(f"{_BASE}/{tid}")
    assert resp.status_code == 409


async def test_delete_provisioning_returns_409(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "provisioning")
    resp = await client.delete(f"{_BASE}/{tid}")
    assert resp.status_code == 409


async def test_delete_active_returns_409(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "active")
    resp = await client.delete(f"{_BASE}/{tid}")
    assert resp.status_code == 409


async def test_delete_suspended_returns_409(client: AsyncClient) -> None:
    tid = (await _create(client))["id"]
    await _force_status(tid, "suspended")
    resp = await client.delete(f"{_BASE}/{tid}")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Other error cases
# ---------------------------------------------------------------------------


async def test_delete_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.delete(f"{_BASE}/{uuid4()}")
    assert resp.status_code == 404


async def test_delete_invalid_uuid_returns_422(client: AsyncClient) -> None:
    resp = await client.delete(f"{_BASE}/not-a-uuid")
    assert resp.status_code == 422


async def test_delete_twice_returns_404(client: AsyncClient) -> None:
    """Soft-deleted tenants are not visible — second delete should 404."""
    tid = (await _create(client))["id"]
    await _force_status(tid, "archived")
    await client.delete(f"{_BASE}/{tid}")

    resp = await client.delete(f"{_BASE}/{tid}")
    assert resp.status_code == 404
