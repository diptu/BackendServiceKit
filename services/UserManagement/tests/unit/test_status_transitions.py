"""User status lifecycle transitions + status-history audit trail."""

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
async def test_suspend_directly_from_pending_is_invalid(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.post(
        f"/api/v1/users/{user_id}/suspend", json={}, headers=_headers(tenant_id)
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_suspend_and_reactivate(client: AsyncClient) -> None:
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
        f"/api/v1/users/{user_id}/activate", json={}, headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"


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
    transitions = [(h["from_status"], h["to_status"]) for h in data["items"]]
    assert ("pending", "active") in transitions
    assert ("active", "suspended") in transitions
