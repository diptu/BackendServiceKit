"""GET .../status — the aggregate view merging UserManagement's record with
this service's own locked/audit metadata."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import FakeUserLifecycleClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_status_before_any_transition_reflects_remote_only(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active", email="a@example.com")

    r = await client.get(
        f"/api/v1/user-lifecycle/{user_id}/status", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["remote_status"] == "active"
    assert body["lifecycle_status"] == "active"
    assert body["locked_reason"] is None
    assert body["last_event_type"] is None


@pytest.mark.asyncio
async def test_status_after_lock_shows_locked_reason_and_last_event(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active")

    await client.post(
        f"/api/v1/user-lifecycle/{user_id}/lock",
        json={"reason": "security hold"},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/user-lifecycle/{user_id}/status", headers=_headers(tenant_id)
    )
    body = r.json()
    assert body["lifecycle_status"] == "locked"
    assert body["locked_reason"] == "security hold"
    assert body["last_event_type"] == "lock"


@pytest.mark.asyncio
async def test_status_unknown_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/user-lifecycle/{uuid.uuid4()}/status", headers=_headers(tenant_id)
    )
    assert r.status_code == 404
