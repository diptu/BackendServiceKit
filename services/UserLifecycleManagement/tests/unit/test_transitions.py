"""Lifecycle transitions: activate/onboard/suspend/unsuspend/lock/unlock/deactivate/offboard."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import FakeUserLifecycleClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_activate_from_pending(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="pending")

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/activate",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    # fire-and-log sync actually landed on the fake remote
    assert fake_client.users[user_id].status == "active"


@pytest.mark.asyncio
async def test_onboard_from_pending_records_distinct_event_type(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="pending")

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/onboard",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    events = await client.get(
        f"/api/v1/user-lifecycle/{user_id}/events", headers=_headers(tenant_id)
    )
    assert events.json()["items"][0]["event_type"] == "onboard"


@pytest.mark.asyncio
async def test_user_not_found_in_user_management(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/user-lifecycle/{uuid.uuid4()}/activate",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_lock_requires_active(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="pending")

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/lock",
        json={"reason": "security hold"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_lock_then_unlock(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active")

    locked_by = uuid.uuid4()
    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/lock",
        json={"reason": "fraud investigation", "locked_by": str(locked_by)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "locked"
    assert body["locked_reason"] == "fraud investigation"
    # locked proxies to suspended on UserManagement's side
    assert fake_client.users[user_id].status == "suspended"

    r2 = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/unlock", json={}, headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"
    assert r2.json()["locked_reason"] is None
    assert fake_client.users[user_id].status == "active"


@pytest.mark.asyncio
async def test_suspend_and_unsuspend(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active")

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/suspend",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"

    r2 = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/unsuspend",
        json={},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"


@pytest.mark.asyncio
async def test_deactivate_is_terminal(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active")

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/deactivate",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "deactivated"

    r2 = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/activate",
        json={},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_offboard_records_distinct_event_type(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active")

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/offboard",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "deactivated"

    events = await client.get(
        f"/api/v1/user-lifecycle/{user_id}/events", headers=_headers(tenant_id)
    )
    assert events.json()["items"][0]["event_type"] == "offboard"
