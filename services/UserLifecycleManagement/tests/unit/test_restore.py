"""Restore — undo a UserManagement-level soft-delete.

Doesn't go through the local state machine (see LifecycleService.restore's
docstring) — exercised independently of VALID_TRANSITIONS.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import FakeUserLifecycleClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_restore_deleted_user(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(
        user_id, tenant_id, status="deactivated", deleted_at=datetime.now(timezone.utc)
    )

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/restore",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["deleted_at"] is None
    assert fake_client.users[user_id].deleted_at is None


@pytest.mark.asyncio
async def test_restore_not_deleted_user(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id, tenant_id, status="active", deleted_at=None)

    r = await client.post(
        f"/api/v1/user-lifecycle/{user_id}/restore",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_restore_unknown_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/user-lifecycle/{uuid.uuid4()}/restore",
        json={},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_restore_records_event(
    client: AsyncClient, fake_client: FakeUserLifecycleClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(
        user_id, tenant_id, status="deactivated", deleted_at=datetime.now(timezone.utc)
    )

    await client.post(
        f"/api/v1/user-lifecycle/{user_id}/restore",
        json={},
        headers=_headers(tenant_id),
    )

    events = await client.get(
        f"/api/v1/user-lifecycle/{user_id}/events", headers=_headers(tenant_id)
    )
    assert events.json()["items"][0]["event_type"] == "restore"
