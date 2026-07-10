"""Full status lifecycle: activate/onboard/suspend/unsuspend/lock/unlock/
deactivate/offboard + status-history audit trail.

Merges UserManagement's activate/suspend/deactivate tests with
UserLifecycleManagement's onboard/unsuspend/lock/unlock/offboard tests —
all now exercised directly against /api/v1/users/{id}/..., no separate
/user-lifecycle prefix needed anymore.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


async def _create_user(client: AsyncClient, tenant_id: uuid.UUID) -> str:
    r = await client.post(
        "/api/v1/users",
        json={
            "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    return str(r.json()["id"])


@pytest.mark.asyncio
async def test_activate_from_pending(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_onboard_from_pending_records_distinct_action(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.post(
        f"/api/v1/users/{user_id}/onboard", json={}, headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    history = await client.get(
        f"/api/v1/users/{user_id}/status-history", headers=_headers(tenant_id)
    )
    assert history.json()["items"][0]["action"] == "onboard"


@pytest.mark.asyncio
async def test_suspend_directly_from_pending_is_invalid(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.post(
        f"/api/v1/users/{user_id}/suspend", json={}, headers=_headers(tenant_id)
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_suspend_and_unsuspend(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)
    await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )

    r = await client.post(
        f"/api/v1/users/{user_id}/suspend",
        json={"reason": "payment overdue"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"

    r2 = await client.post(
        f"/api/v1/users/{user_id}/unsuspend", json={}, headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"


@pytest.mark.asyncio
async def test_lock_requires_active(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.post(
        f"/api/v1/users/{user_id}/lock",
        json={"reason": "security hold"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_lock_then_unlock(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)
    await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )

    locked_by = uuid.uuid4()
    r = await client.post(
        f"/api/v1/users/{user_id}/lock",
        json={"reason": "fraud investigation", "locked_by": str(locked_by)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "locked"
    assert body["locked_reason"] == "fraud investigation"
    assert body["locked_by"] == str(locked_by)

    r2 = await client.post(
        f"/api/v1/users/{user_id}/unlock", json={}, headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"
    assert r2.json()["locked_reason"] is None


@pytest.mark.asyncio
async def test_deactivate_is_terminal(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)
    await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )

    r = await client.post(
        f"/api/v1/users/{user_id}/deactivate", json={}, headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "deactivated"

    r2 = await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_offboard_records_distinct_action(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)
    await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )

    r = await client.post(
        f"/api/v1/users/{user_id}/offboard", json={}, headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "deactivated"

    history = await client.get(
        f"/api/v1/users/{user_id}/status-history", headers=_headers(tenant_id)
    )
    assert history.json()["items"][0]["action"] == "offboard"


@pytest.mark.asyncio
async def test_status_history_records_every_transition(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)
    await client.post(
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )
    await client.post(
        f"/api/v1/users/{user_id}/suspend",
        json={"reason": "policy violation"},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/users/{user_id}/status-history", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    transitions = [
        (h["from_status"], h["to_status"], h["action"]) for h in data["items"]
    ]
    assert ("pending", "active", "activate") in transitions
    assert ("active", "suspended", "suspend") in transitions
