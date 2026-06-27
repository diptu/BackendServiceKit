"""API-level tests for tenant lifecycle transition endpoints.

Covers:
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/activate
  POST /api/v1/tenant-lifecycle/{tenant_id}/suspend
  POST /api/v1/tenant-lifecycle/{tenant_id}/reactivate
  POST /api/v1/tenant-lifecycle/{tenant_id}/lock
  POST /api/v1/tenant-lifecycle/{tenant_id}/archive
  POST /api/v1/tenant-lifecycle/{tenant_id}/delete
  GET  /api/v1/tenant-lifecycle/{tenant_id}/history

State machine:
  (unknown) → provisioning  [auto-created by activate]
  provisioning → active
  active    → suspended | locked | archived
  suspended → active | archived
  locked    → archived
  archived  → deleted
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
from app.models import TenantLifecycleEvent, TenantLifecycleState  # noqa: F401

# ---------------------------------------------------------------------------
# Shared in-memory test database
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

_BASE = "/api/v1/tenant-lifecycle"


async def _seed_tenant(tenant_id: UUID, status: str = "provisioning") -> None:
    """Insert a lifecycle state record directly, bypassing the API."""
    from datetime import datetime, timezone
    async with _SESSION_FACTORY() as s:
        s.add(
            TenantLifecycleState(
                id=uuid4(),
                tenant_id=tenant_id,
                current_status=status,
                previous_status=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await s.commit()


async def _force_status(tenant_id: UUID, status: str) -> None:
    """Bypass the state machine and directly set a tenant's lifecycle status."""
    async with _SESSION_FACTORY() as s:
        await s.execute(
            update(TenantLifecycleState)
            .where(TenantLifecycleState.tenant_id == tenant_id)
            .values(current_status=status)
        )
        await s.commit()


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/activate  (idempotent)
# ---------------------------------------------------------------------------


async def test_activate_from_provisioning(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_activate_from_active_is_idempotent(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_activate_unknown_tenant_auto_creates_and_activates(client: AsyncClient) -> None:
    # activate auto-creates a provisioning record when the tenant is not yet registered
    resp = await client.put(f"{_BASE}/{uuid4()}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_activate_reason_too_long_returns_422(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={"reason": "x" * 501})
    assert resp.status_code == 422


async def test_activate_response_shape(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    body = (await client.put(f"{_BASE}/{tid}/activate", json={})).json()
    for key in ("tenant_id", "current_status", "previous_status", "updated_at"):
        assert key in body, f"missing key: {key}"
    assert body["tenant_id"] == str(tid)
    assert body["current_status"] == "active"
    assert body["previous_status"] == "provisioning"


# ---------------------------------------------------------------------------
# POST /{tenant_id}/suspend
# ---------------------------------------------------------------------------


async def test_suspend_from_active(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "suspended"


async def test_suspend_from_pending_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_from_suspended_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/suspend", json={})
    assert resp.status_code == 404


async def test_suspend_with_reason(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.post(
        f"{_BASE}/{tid}/suspend",
        json={"reason": "Non-payment — subscription expired."},
    )
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "suspended"


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/suspend  (idempotent)
# ---------------------------------------------------------------------------


async def test_suspend_put_from_active(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "suspended"


async def test_suspend_put_idempotent_when_already_suspended(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.put(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "suspended"


async def test_suspend_put_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/suspend", json={})
    assert resp.status_code == 404


async def test_suspend_put_from_provisioning_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.put(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_put_from_archived_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")

    resp = await client.put(f"{_BASE}/{tid}/suspend", json={})
    assert resp.status_code == 409


async def test_suspend_put_reason_too_long_returns_422(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/suspend", json={"reason": "x" * 501})
    assert resp.status_code == 422


async def test_suspend_put_response_shape(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    body = (await client.put(f"{_BASE}/{tid}/suspend", json={"reason": "billing hold"})).json()
    for key in ("tenant_id", "current_status", "previous_status", "updated_at"):
        assert key in body, f"missing key: {key}"
    assert body["tenant_id"] == str(tid)
    assert body["current_status"] == "suspended"
    assert body["previous_status"] == "active"


# ---------------------------------------------------------------------------
# POST /{tenant_id}/reactivate
# ---------------------------------------------------------------------------


async def test_reactivate_from_suspended(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/reactivate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_reactivate_from_active_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/reactivate", json={})
    assert resp.status_code == 409


async def test_reactivate_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/reactivate", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /{tenant_id}/lock
# ---------------------------------------------------------------------------


async def test_lock_from_active(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/lock", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "locked"


async def test_lock_from_suspended_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/lock", json={})
    assert resp.status_code == 409


async def test_lock_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/lock", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /{tenant_id}/archive
# ---------------------------------------------------------------------------


async def test_archive_from_active(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "archived"


async def test_archive_from_suspended(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "archived"


async def test_archive_from_locked(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "locked")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "archived"


async def test_archive_from_pending_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_from_archived_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")

    resp = await client.post(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/archive", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /{tenant_id}/delete
# ---------------------------------------------------------------------------


async def test_delete_from_archived(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")

    resp = await client.post(f"{_BASE}/{tid}/delete", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "deleted"


async def test_delete_from_active_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.post(f"{_BASE}/{tid}/delete", json={})
    assert resp.status_code == 409


async def test_delete_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.post(f"{_BASE}/{uuid4()}/delete", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /{tenant_id}/history
# ---------------------------------------------------------------------------


async def test_history_returns_events(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    await client.put(f"{_BASE}/{tid}/activate", json={})
    await client.post(f"{_BASE}/{tid}/suspend", json={"reason": "maintenance"})

    resp = await client.get(f"{_BASE}/{tid}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == str(tid)
    assert body["total"] == 2
    assert len(body["events"]) == 2
    # newest first
    assert body["events"][0]["to_status"] == "suspended"
    assert body["events"][1]["to_status"] == "active"


async def test_history_empty_for_no_transitions(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.get(f"{_BASE}/{tid}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["events"] == []


async def test_history_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/{uuid4()}/history")
    assert resp.status_code == 404


async def test_history_event_shape(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")
    await client.put(f"{_BASE}/{tid}/activate", json={"reason": "provisioning done"})

    body = (await client.get(f"{_BASE}/{tid}/history")).json()
    event = body["events"][0]
    for key in (
        "id", "tenant_id", "from_status", "to_status",
        "transition", "reason", "performed_by", "source", "occurred_at",
    ):
        assert key in event, f"missing key: {key}"
    assert event["from_status"] == "provisioning"
    assert event["to_status"] == "active"
    assert event["transition"] == "activate"
    assert event["reason"] == "provisioning done"
    assert event["source"] == "api"


async def test_history_invalid_uuid_returns_422(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/not-a-uuid/history")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Full state machine path
# ---------------------------------------------------------------------------


async def test_full_lifecycle_path(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    r = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "active"

    r = await client.post(f"{_BASE}/{tid}/suspend", json={"reason": "maintenance"})
    assert r.status_code == 200
    assert r.json()["current_status"] == "suspended"

    r = await client.post(f"{_BASE}/{tid}/reactivate", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "active"

    r = await client.post(f"{_BASE}/{tid}/archive", json={"reason": "end of contract"})
    assert r.status_code == 200
    assert r.json()["current_status"] == "archived"

    r = await client.post(f"{_BASE}/{tid}/delete", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "deleted"

    history = (await client.get(f"{_BASE}/{tid}/history")).json()
    assert history["total"] == 5


async def test_deleted_state_is_terminal(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")
    await client.post(f"{_BASE}/{tid}/delete", json={})

    for action in ("suspend", "reactivate", "lock", "archive", "delete"):
        resp = await client.post(f"{_BASE}/{tid}/{action}", json={})
        assert resp.status_code == 409, f"expected 409 for {action} from deleted"

    # activate uses PUT; DELETED → ACTIVE is not a valid transition
    resp = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 409, "expected 409 for activate from deleted"
