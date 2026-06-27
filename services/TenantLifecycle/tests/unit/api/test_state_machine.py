"""State machine contract tests — TenantLifecycle service.

This file is the AUTHORITATIVE CONTRACT for the TL state machine.
It encodes the exact diagram from README.md as executable assertions.
If the state machine needs to change, update this file first.

Enforced diagram:

    (new tenant, entry via TM draft state)
             |
             v  PUT /provisioning
        provisioning
             |
             v  PUT /pending          ← mandatory compliance gate
           pending
             |
             v  PUT /activate
           active
             │
             ├──> suspended <──────> active   (PUT /suspend / PUT /reactivate)
             │        │
             │        └──> archived ──> deleted
             │
             ├──> locked <────────> active    (PUT /lock / PUT /unlock)
             │        │
             │        └──> archived ──> deleted
             │
             └──> archived ────────> deleted  (PUT /archive / PUT /delete)

Key invariants:
  1. provisioning → pending is mandatory before activation (no shortcut to active).
  2. deleted is ONLY reachable via archived (no direct deletion from operational states).
  3. suspended → provisioning is never allowed (forward-only once operational).
  4. provisioning → active is never allowed (pending gate cannot be skipped).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app
from app.models import TenantLifecycleEvent, TenantLifecycleState  # noqa: F401

# ---------------------------------------------------------------------------
# In-memory test database shared across all tests in this module
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
async def _db() -> None:
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


_BASE = "/api/v1/tenant-lifecycle"


async def _seed(tenant_id: UUID, status: str) -> None:
    """Bypass the API and seed a lifecycle record at an arbitrary state."""
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


# ---------------------------------------------------------------------------
# Valid transitions — every row must produce HTTP 200
# ---------------------------------------------------------------------------

_VALID: list[tuple[str, str, str]] = [
    # (seed_status, http_method, endpoint_suffix)
    ("provisioning", "PUT",  "/pending"),        # provisioning → pending (gate)
    ("pending",      "PUT",  "/activate"),        # pending      → active
    ("active",       "PUT",  "/suspend"),         # active       → suspended (idempotent)
    ("active",       "PUT", "/lock"),            # active       → locked
    ("active",       "PUT", "/archive"),         # active       → archived
    ("suspended",    "PUT", "/reactivate"),      # suspended    → active
    ("suspended",    "PUT", "/archive"),         # suspended    → archived
    ("locked",       "PUT", "/unlock"),          # locked       → active
    ("locked",       "PUT", "/archive"),         # locked       → archived
    ("archived",     "PUT", "/delete"),          # archived     → deleted  (only deletion path)
    # Idempotent re-entries
    ("provisioning", "PUT",  "/provisioning"),   # already provisioning → 200
    ("pending",      "PUT",  "/pending"),         # already pending → 200
    ("active",       "PUT",  "/activate"),        # already active → 200
    ("suspended",    "PUT",  "/suspend"),         # already suspended → 200
]

_VALID_IDS = [
    f"{s}─{m}─{e.strip('/')}" for s, m, e in _VALID
]


@pytest.mark.parametrize("seed,method,endpoint", _VALID, ids=_VALID_IDS)
async def test_valid_transition(
    seed: str, method: str, endpoint: str, client: AsyncClient
) -> None:
    """Every valid transition must return 200."""
    tid = uuid4()
    await _seed(tid, seed)
    resp = await getattr(client, method.lower())(f"{_BASE}/{tid}{endpoint}", json={})
    assert resp.status_code == 200, (
        f"Expected 200 for {seed} ─{method}→ {endpoint}, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Blocked transitions — every row must produce HTTP 409
# ---------------------------------------------------------------------------

_BLOCKED: list[tuple[str, str, str]] = [
    # ── Pending gate must not be skipped ──────────────────────────────────
    ("provisioning", "PUT",  "/activate"),        # skip pending → blocked
    # ── provisioning cannot go backward or sideways ───────────────────────
    ("provisioning", "PUT", "/lock"),
    ("provisioning", "PUT", "/reactivate"),
    ("provisioning", "PUT", "/archive"),
    ("provisioning", "PUT", "/delete"),          # no direct deletion
    # ── pending cannot skip forward or go sideways ────────────────────────
    ("pending",      "PUT",  "/provisioning"),    # re-provision from pending → blocked
    ("pending",      "PUT",  "/suspend"),
    ("pending",      "PUT", "/lock"),
    ("pending",      "PUT", "/reactivate"),
    ("pending",      "PUT", "/archive"),
    ("pending",      "PUT", "/delete"),          # no direct deletion
    # ── active has no deletion shortcut ───────────────────────────────────
    ("active",       "PUT", "/delete"),          # must archive first
    ("active",       "PUT",  "/provisioning"),    # re-provision from active → blocked
    ("active",       "PUT", "/reactivate"),      # reactivate only from suspended
    ("active",       "PUT", "/unlock"),          # unlock only from locked
    # ── suspended cannot re-provision or skip to delete ───────────────────
    ("suspended",    "PUT",  "/provisioning"),    # THE critical invariant
    ("suspended",    "PUT",  "/activate"),        # must use reactivate endpoint
    ("suspended",    "PUT", "/delete"),          # no direct deletion
    ("suspended",    "PUT", "/lock"),            # lock only from active
    ("suspended",    "PUT", "/unlock"),          # unlock only from locked
    # ── locked cannot bypass archive or go sideways ───────────────────────
    ("locked",       "PUT",  "/provisioning"),
    ("locked",       "PUT",  "/activate"),        # must use unlock endpoint
    ("locked",       "PUT",  "/suspend"),
    ("locked",       "PUT", "/reactivate"),
    ("locked",       "PUT", "/lock"),
    ("locked",       "PUT", "/delete"),          # no direct deletion
    # ── archived is almost terminal (only delete allowed) ─────────────────
    ("archived",     "PUT",  "/provisioning"),
    ("archived",     "PUT",  "/pending"),
    ("archived",     "PUT",  "/activate"),
    ("archived",     "PUT",  "/suspend"),
    ("archived",     "PUT", "/reactivate"),
    ("archived",     "PUT", "/lock"),
    ("archived",     "PUT", "/unlock"),
    ("archived",     "PUT", "/archive"),
    # ── deleted is terminal — nothing is allowed ───────────────────────────
    ("deleted",      "PUT",  "/provisioning"),
    ("deleted",      "PUT",  "/pending"),
    ("deleted",      "PUT",  "/activate"),
    ("deleted",      "PUT",  "/suspend"),
    ("deleted",      "PUT", "/reactivate"),
    ("deleted",      "PUT", "/lock"),
    ("deleted",      "PUT", "/unlock"),
    ("deleted",      "PUT", "/archive"),
    ("deleted",      "PUT", "/delete"),
]

_BLOCKED_IDS = [
    f"{s}─{m}─{e.strip('/')}" for s, m, e in _BLOCKED
]


@pytest.mark.parametrize("seed,method,endpoint", _BLOCKED, ids=_BLOCKED_IDS)
async def test_blocked_transition(
    seed: str, method: str, endpoint: str, client: AsyncClient
) -> None:
    """Every invalid transition must return 409."""
    tid = uuid4()
    await _seed(tid, seed)
    resp = await getattr(client, method.lower())(f"{_BASE}/{tid}{endpoint}", json={})
    assert resp.status_code == 409, (
        f"Expected 409 for {seed} ─{method}→ {endpoint}, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Full happy path — end-to-end lifecycle traversal via the API
# ---------------------------------------------------------------------------


async def test_full_lifecycle_via_api(client: AsyncClient) -> None:
    """Walk the complete lifecycle through the API (no DB seeding)."""
    tid = uuid4()

    # Entry point
    r = await client.put(f"{_BASE}/{tid}/provisioning", json={})
    assert r.status_code == 200 and r.json()["current_status"] == "provisioning"

    # Mandatory pending gate
    r = await client.put(f"{_BASE}/{tid}/pending", json={"reason": "infra ready"})
    assert r.status_code == 200 and r.json()["current_status"] == "pending"
    assert r.json()["previous_status"] == "provisioning"

    # Activate
    r = await client.put(f"{_BASE}/{tid}/activate", json={"reason": "compliance cleared"})
    assert r.status_code == 200 and r.json()["current_status"] == "active"
    assert r.json()["previous_status"] == "pending"

    # Suspend and reactivate
    r = await client.put(f"{_BASE}/{tid}/suspend", json={"reason": "non-payment"})
    assert r.status_code == 200 and r.json()["current_status"] == "suspended"

    r = await client.put(f"{_BASE}/{tid}/reactivate", json={})
    assert r.status_code == 200 and r.json()["current_status"] == "active"

    # Lock and unlock
    r = await client.put(f"{_BASE}/{tid}/lock", json={"reason": "unusual API traffic"})
    assert r.status_code == 200 and r.json()["current_status"] == "locked"

    r = await client.put(f"{_BASE}/{tid}/unlock", json={"reason": "investigation complete"})
    assert r.status_code == 200 and r.json()["current_status"] == "active"

    # Archive → delete (only valid deletion path)
    r = await client.put(f"{_BASE}/{tid}/archive", json={"reason": "contract ended"})
    assert r.status_code == 200 and r.json()["current_status"] == "archived"

    r = await client.put(f"{_BASE}/{tid}/delete", json={})
    assert r.status_code == 200 and r.json()["current_status"] == "deleted"

    # Verify full event history (all 9 fit on one page, so next_cursor is null)
    history = (await client.get(f"{_BASE}/{tid}/history")).json()
    assert history["total"] == 9
    assert history["next_cursor"] is None
    statuses = [e["to_status"] for e in reversed(history["events"])]
    assert statuses == [
        "provisioning", "pending", "active",
        "suspended", "active",
        "locked", "active",
        "archived", "deleted",
    ]


async def test_lock_then_archive_path(client: AsyncClient) -> None:
    """locked → archived → deleted (alternative terminal path from lock)."""
    tid = uuid4()
    await _seed(tid, "locked")

    r = await client.put(f"{_BASE}/{tid}/archive", json={"reason": "breach confirmed"})
    assert r.status_code == 200 and r.json()["current_status"] == "archived"

    r = await client.put(f"{_BASE}/{tid}/delete", json={})
    assert r.status_code == 200 and r.json()["current_status"] == "deleted"


async def test_suspended_archive_path(client: AsyncClient) -> None:
    """suspended → archived → deleted (tenant never reactivated)."""
    tid = uuid4()
    await _seed(tid, "suspended")

    r = await client.put(f"{_BASE}/{tid}/archive", json={"reason": "contract not renewed"})
    assert r.status_code == 200 and r.json()["current_status"] == "archived"

    r = await client.put(f"{_BASE}/{tid}/delete", json={})
    assert r.status_code == 200 and r.json()["current_status"] == "deleted"


# ---------------------------------------------------------------------------
# Idempotency contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status,method,endpoint", [
    ("provisioning", "PUT", "/provisioning"),
    ("pending",      "PUT", "/pending"),
    ("active",       "PUT", "/activate"),
    ("suspended",    "PUT", "/suspend"),
])
async def test_idempotent_endpoints(
    status: str, method: str, endpoint: str, client: AsyncClient
) -> None:
    """PUT endpoints are idempotent: re-calling from the target state returns 200."""
    tid = uuid4()
    await _seed(tid, status)
    for _ in range(2):
        resp = await getattr(client, method.lower())(f"{_BASE}/{tid}{endpoint}", json={})
        assert resp.status_code == 200
        assert resp.json()["current_status"] == status


# ---------------------------------------------------------------------------
# 404 for unregistered tenants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,endpoint", [
    ("PUT",  "/pending"),
    ("PUT",  "/activate"),
    ("PUT",  "/suspend"),
    ("PUT", "/reactivate"),
    ("PUT", "/lock"),
    ("PUT", "/unlock"),
    ("PUT", "/archive"),
    ("PUT", "/delete"),
    ("GET",  "/history"),
])
async def test_unregistered_tenant_returns_404(
    method: str, endpoint: str, client: AsyncClient
) -> None:
    """Any transition on a tenant not yet registered with TL returns 404."""
    call = getattr(client, method.lower())
    kwargs = {} if method == "GET" else {"json": {}}
    resp = await call(f"{_BASE}/{uuid4()}{endpoint}", **kwargs)
    assert resp.status_code == 404
