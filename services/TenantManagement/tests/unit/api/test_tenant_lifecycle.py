"""API-level tests for tenant lifecycle transition endpoints.

Covers:
  POST /api/v1/tenants/{tenant_id}/provision
  POST /api/v1/tenants/{tenant_id}/pend
  POST /api/v1/tenants/{tenant_id}/activate
  POST /api/v1/tenants/{tenant_id}/suspend
  POST /api/v1/tenants/{tenant_id}/archive

State machine (per CLAUDE.md):
  draft        → provisioning | deleted
  provisioning → pending
  pending      → active       | deleted
  active       → suspended    | archived
  suspended    → active       | archived
  archived     → deleted
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

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
# Shared in-memory test database
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


async def _create_tenant(client: AsyncClient, name: str = "acme-corp") -> str:
    """POST /tenants and return the new tenant UUID string."""
    resp = await client.post(
        _BASE,
        json={
            "name": name,
            "display_name": name.title(),
            "owner_id": _OWNER,
            "region": "us-east-1",
            "timezone": "UTC",
            "locale": "en-US",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def _force_status(tenant_id: str, status: str) -> None:
    """Bypass the state machine and directly set a tenant's status in the DB."""
    async with _SESSION_FACTORY() as s:
        await s.execute(
            update(Tenant).where(Tenant.id == UUID(tenant_id)).values(status=status)
        )
        await s.commit()


# ---------------------------------------------------------------------------
# POST /{tenant_id}/pend
# ---------------------------------------------------------------------------


async def test_pend_from_provisioning(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "provisioning")

    resp = await client.post(f"{_BASE}/{tid}/pend", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


async def test_pend_from_draft_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)

    resp = await client.post(f"{_BASE}/{tid}/pend", json={})
    assert resp.status_code == 409


async def test_pend_from_pending_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "pending")

    resp = await client.post(f"{_BASE}/{tid}/pend", json={})
    assert resp.status_code == 409


async def test_pend_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/pend", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /{tenant_id}/activate
# ---------------------------------------------------------------------------


async def test_activate_from_provisioning_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "provisioning")

    resp = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 409


async def test_activate_from_pending(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "pending")

    resp = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_activate_from_suspended(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_activate_from_draft_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    # tenant is in draft state; activate is not a valid transition from draft
    resp = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 409


async def test_activate_from_archived_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "archived")

    resp = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 409


async def test_activate_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/activate", json={})
    assert resp.status_code == 404


async def test_activate_with_reason(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "pending")

    resp = await client.post(
        f"{_BASE}/{tid}/activate",
        json={"reason": "Compliance review passed — all resources ready."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_activate_reason_too_long_returns_422(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "pending")

    resp = await client.post(
        f"{_BASE}/{tid}/activate",
        json={"reason": "x" * 501},
    )
    assert resp.status_code == 422


async def test_activate_response_shape(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "pending")

    body = (await client.post(f"{_BASE}/{tid}/activate", json={})).json()
    for key in ("id", "name", "status", "region", "created_at", "updated_at"):
        assert key in body, f"missing key: {key}"
    assert body["id"] == tid


# ---------------------------------------------------------------------------
# POST /{tenant_id}/suspend
# ---------------------------------------------------------------------------


async def test_suspend_from_active(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"


async def test_suspend_from_active_with_reason(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "active")

    resp = await client.post(
        f"{_BASE}/{tid}/suspend",
        json={"reason": "Non-payment — subscription expired 2026-06-01."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"


async def test_suspend_from_draft_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_from_provisioning_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "provisioning")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_from_suspended_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_from_archived_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "archived")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/suspend", json={})
    assert resp.status_code == 404


async def test_suspend_reason_too_long_returns_422(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={"reason": "y" * 501})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /{tenant_id}/archive
# ---------------------------------------------------------------------------


async def test_archive_from_active(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


async def test_archive_from_suspended(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


async def test_archive_from_draft_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_from_provisioning_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "provisioning")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_from_archived_returns_409(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "archived")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/archive", json={})
    assert resp.status_code == 404


async def test_archive_with_reason(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "active")

    resp = await client.post(
        f"{_BASE}/{tid}/archive",
        json={"reason": "Customer churned — contract ended 2026-05-31."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


async def test_archive_reason_too_long_returns_422(client: AsyncClient) -> None:
    tid = await _create_tenant(client)
    await _force_status(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={"reason": "z" * 501})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Full lifecycle path: draft → provisioning → pending → active → suspended → active → archived
# ---------------------------------------------------------------------------


async def test_full_lifecycle_path(client: AsyncClient) -> None:
    tid = await _create_tenant(client, name="lifecycle-tenant")

    r = await client.post(f"{_BASE}/{tid}/provision", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "provisioning"

    r = await client.post(f"{_BASE}/{tid}/pend", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"

    r = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    r = await client.post(f"{_BASE}/{tid}/suspend", json={"reason": "maintenance"})
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"

    r = await client.post(f"{_BASE}/{tid}/activate", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    r = await client.post(f"{_BASE}/{tid}/archive", json={"reason": "end of life"})
    assert r.status_code == 200
    assert r.json()["status"] == "archived"
