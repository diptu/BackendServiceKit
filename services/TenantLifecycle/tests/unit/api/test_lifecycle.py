"""API-level tests for individual tenant lifecycle transition endpoints.

Covers each endpoint in isolation. For the complete state machine contract
(all valid + invalid transitions, full lifecycle path) see test_state_machine.py.

Endpoints covered:
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/provisioning
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/pending
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/activate
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/suspend
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/reactivate
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/lock
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/unlock
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/archive
  PUT  /api/v1/tenant-lifecycle/{tenant_id}/delete
  GET  /api/v1/tenant-lifecycle/{tenant_id}/history
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
# PUT /{tenant_id}/provisioning
# ---------------------------------------------------------------------------


async def test_provision_new_tenant_creates_provisioning_state(client: AsyncClient) -> None:
    tid = uuid4()
    resp = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_status"] == "provisioning"
    assert body["previous_status"] is None
    assert body["tenant_id"] == str(tid)


async def test_provision_idempotent_when_already_provisioning(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")
    resp = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "provisioning"


async def test_provision_when_active_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")
    resp = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert resp.status_code == 409


async def test_provision_when_suspended_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")
    resp = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert resp.status_code == 409


async def test_provision_response_shape(client: AsyncClient) -> None:
    tid = uuid4()
    resp = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert resp.status_code == 200
    body = resp.json()
    for key in ("tenant_id", "current_status", "previous_status", "updated_at"):
        assert key in body, f"missing key: {key}"


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/activate  (idempotent)
# ---------------------------------------------------------------------------


async def test_activate_from_provisioning_returns_409(client: AsyncClient) -> None:
    """provisioning → active is blocked; must go through pending first."""
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 409


async def test_activate_from_pending(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "pending")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_activate_from_active_is_idempotent(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_activate_unknown_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/activate", json={})
    assert resp.status_code == 404


async def test_activate_reason_too_long_returns_422(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "pending")

    resp = await client.put(f"{_BASE}/{tid}/activate", json={"reason": "x" * 501})
    assert resp.status_code == 422


async def test_activate_response_shape(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "pending")

    body = (await client.put(f"{_BASE}/{tid}/activate", json={})).json()
    for key in ("tenant_id", "current_status", "previous_status", "updated_at"):
        assert key in body, f"missing key: {key}"
    assert body["tenant_id"] == str(tid)
    assert body["current_status"] == "active"
    assert body["previous_status"] == "pending"


async def test_suspend_with_reason(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(
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
# PUT /{tenant_id}/reactivate
# ---------------------------------------------------------------------------


async def test_reactivate_from_suspended(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.put(f"{_BASE}/{tid}/reactivate", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_reactivate_from_active_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/reactivate", json={})
    assert resp.status_code == 409


async def test_reactivate_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/reactivate", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/lock
# ---------------------------------------------------------------------------


async def test_lock_from_active(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/lock", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "locked"


async def test_lock_from_suspended_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.put(f"{_BASE}/{tid}/lock", json={})
    assert resp.status_code == 409


async def test_lock_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/lock", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/unlock
# ---------------------------------------------------------------------------


async def test_unlock_from_locked(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "locked")

    resp = await client.put(f"{_BASE}/{tid}/unlock", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"
    assert resp.json()["previous_status"] == "locked"


async def test_unlock_with_reason(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "locked")

    resp = await client.put(f"{_BASE}/{tid}/unlock", json={"reason": "Investigation complete — no breach confirmed."})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "active"


async def test_unlock_from_active_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/unlock", json={})
    assert resp.status_code == 409


async def test_unlock_from_suspended_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.put(f"{_BASE}/{tid}/unlock", json={})
    assert resp.status_code == 409


async def test_unlock_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/unlock", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/archive
# ---------------------------------------------------------------------------


async def test_archive_from_active(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "archived"


async def test_archive_from_suspended(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "suspended")

    resp = await client.put(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "archived"


async def test_archive_from_locked(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "locked")

    resp = await client.put(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "archived"


async def test_archive_from_provisioning_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.put(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_from_archived_returns_409(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")

    resp = await client.put(f"{_BASE}/{tid}/archive", json={})
    assert resp.status_code == 409


async def test_archive_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/archive", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{tenant_id}/delete
# ---------------------------------------------------------------------------


async def test_delete_from_archived(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")

    resp = await client.put(f"{_BASE}/{tid}/delete", json={})
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "deleted"


async def test_delete_from_active_returns_409(client: AsyncClient) -> None:
    """Direct deletion from active is blocked; must archive first."""
    tid = uuid4()
    await _seed_tenant(tid, "active")

    resp = await client.put(f"{_BASE}/{tid}/delete", json={})
    assert resp.status_code == 409


async def test_delete_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.put(f"{_BASE}/{uuid4()}/delete", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /{tenant_id}/history
# ---------------------------------------------------------------------------


async def test_history_returns_events(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "pending")

    await client.put(f"{_BASE}/{tid}/activate", json={})
    await client.put(f"{_BASE}/{tid}/suspend", json={"reason": "maintenance"})
    await client.put(f"{_BASE}/{tid}/reactivate", json={})

    resp = await client.get(f"{_BASE}/{tid}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == str(tid)
    assert body["total"] == 3
    assert len(body["events"]) == 3
    assert body["next_cursor"] is None  # all events fit on first page
    # newest first
    assert body["events"][0]["to_status"] == "active"
    assert body["events"][1]["to_status"] == "suspended"
    assert body["events"][2]["to_status"] == "active"


async def test_history_cursor_pagination(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "pending")

    # Create 3 events
    await client.put(f"{_BASE}/{tid}/activate", json={})
    await client.put(f"{_BASE}/{tid}/suspend", json={})
    await client.put(f"{_BASE}/{tid}/reactivate", json={})

    # First page: limit=2
    page1 = (await client.get(f"{_BASE}/{tid}/history", params={"limit": 2})).json()
    assert len(page1["events"]) == 2
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    # Second page: use cursor
    page2 = (await client.get(
        f"{_BASE}/{tid}/history",
        params={"limit": 2, "next_cursor": page1["next_cursor"]},
    )).json()
    assert len(page2["events"]) == 1
    assert page2["has_more"] is False
    assert page2["next_cursor"] is None

    # No overlap
    ids1 = {e["id"] for e in page1["events"]}
    ids2 = {e["id"] for e in page2["events"]}
    assert ids1.isdisjoint(ids2)

    # Together they cover all 3 events
    assert len(ids1 | ids2) == 3


async def test_history_empty_for_no_transitions(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "provisioning")

    resp = await client.get(f"{_BASE}/{tid}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["events"] == []
    assert body["next_cursor"] is None


async def test_history_missing_tenant_returns_404(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/{uuid4()}/history")
    assert resp.status_code == 404


async def test_history_event_shape(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "pending")
    await client.put(f"{_BASE}/{tid}/activate", json={"reason": "compliance cleared"})

    body = (await client.get(f"{_BASE}/{tid}/history")).json()
    event = body["events"][0]
    for key in (
        "id", "tenant_id", "from_status", "to_status",
        "transition", "reason", "performed_by", "source", "occurred_at",
    ):
        assert key in event, f"missing key: {key}"
    assert event["from_status"] == "pending"
    assert event["to_status"] == "active"
    assert event["transition"] == "activate"
    assert event["reason"] == "compliance cleared"
    assert event["source"] == "api"


async def test_history_invalid_uuid_returns_422(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/not-a-uuid/history")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Full state machine path
# ---------------------------------------------------------------------------


async def test_full_lifecycle_path(client: AsyncClient) -> None:
    tid = uuid4()

    r = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "provisioning"

    r = await client.put(f"{_BASE}/{tid}/pending", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "pending"

    r = await client.put(f"{_BASE}/{tid}/activate", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "active"

    r = await client.put(f"{_BASE}/{tid}/suspend", json={"reason": "maintenance"})
    assert r.status_code == 200
    assert r.json()["current_status"] == "suspended"

    r = await client.put(f"{_BASE}/{tid}/reactivate", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "active"

    r = await client.put(f"{_BASE}/{tid}/archive", json={"reason": "end of contract"})
    assert r.status_code == 200
    assert r.json()["current_status"] == "archived"

    r = await client.put(f"{_BASE}/{tid}/delete", json={})
    assert r.status_code == 200
    assert r.json()["current_status"] == "deleted"

    history = (await client.get(f"{_BASE}/{tid}/history")).json()
    assert history["total"] == 7


async def test_deleted_state_is_terminal(client: AsyncClient) -> None:
    tid = uuid4()
    await _seed_tenant(tid, "archived")
    await client.put(f"{_BASE}/{tid}/delete", json={})

    for action in ("reactivate", "lock", "unlock", "archive", "delete"):
        resp = await client.put(f"{_BASE}/{tid}/{action}", json={})
        assert resp.status_code == 409, f"expected 409 for {action} from deleted"

    for put_action in ("activate", "pending", "suspend"):
        resp = await client.put(f"{_BASE}/{tid}/{put_action}", json={})
        assert resp.status_code == 409, f"expected 409 for PUT /{put_action} from deleted"
