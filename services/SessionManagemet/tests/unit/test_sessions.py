"""Session lifecycle: create, get, list, /me, refresh, revoke, revoke-all,
user-scoped endpoints, and cross-tenant isolation."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


async def _create(
    client: AsyncClient, tenant_id: uuid.UUID, user_id: uuid.UUID, **over: Any
) -> Any:
    body: dict[str, Any] = {"user_id": str(user_id)}
    body.update(over)
    r = await client.post("/api/v1/sessions", json=body, headers=_headers(tenant_id))
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_create_returns_token_and_active_session(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    created = await _create(
        client, tenant_id, user_id, device_info="iPhone", ip_address="1.2.3.4"
    )
    assert created["session_token"]
    assert created["session"]["status"] == "active"
    assert created["session"]["device_info"] == "iPhone"


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    created = await _create(client, tenant_id, user_id)
    sid = created["session"]["id"]
    r = await client.get(f"/api/v1/sessions/{sid}", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["id"] == sid


@pytest.mark.asyncio
async def test_get_unknown_session_404(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/sessions/{uuid.uuid4()}", headers=_headers(tenant_id)
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_and_active_filter(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    a = await _create(client, tenant_id, user_id)
    await _create(client, tenant_id, user_id)
    # Revoke one; active_only should then return one fewer.
    await client.delete(
        f"/api/v1/sessions/{a['session']['id']}", headers=_headers(tenant_id)
    )

    r_all = await client.get(
        "/api/v1/sessions",
        params={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r_all.json()["total"] == 2
    r_active = await client.get(
        "/api/v1/sessions",
        params={"user_id": str(user_id), "active_only": True},
        headers=_headers(tenant_id),
    )
    assert r_active.json()["total"] == 1


@pytest.mark.asyncio
async def test_sessions_me_via_token(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    created = await _create(client, tenant_id, user_id)
    token = str(created["session_token"])
    r = await client.get(
        "/api/v1/sessions/me",
        headers={**_headers(tenant_id), "X-Session-Token": token},
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["session"]["id"]


@pytest.mark.asyncio
async def test_sessions_me_bad_token_401(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.get(
        "/api/v1/sessions/me",
        headers={**_headers(tenant_id), "X-Session-Token": "nope"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_extends_expiry(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    created = await _create(client, tenant_id, user_id, ttl_seconds=10)
    sid = created["session"]["id"]
    original_expiry = created["session"]["expires_at"]
    r = await client.post(
        f"/api/v1/sessions/{sid}/refresh", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["expires_at"] > original_expiry


@pytest.mark.asyncio
async def test_revoke_is_idempotent_and_marks_revoked(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    created = await _create(client, tenant_id, user_id)
    sid = created["session"]["id"]
    r1 = await client.delete(f"/api/v1/sessions/{sid}", headers=_headers(tenant_id))
    assert r1.status_code == 204
    # Second revoke is a no-op, not an error.
    r2 = await client.delete(f"/api/v1/sessions/{sid}", headers=_headers(tenant_id))
    assert r2.status_code == 204
    r = await client.get(f"/api/v1/sessions/{sid}", headers=_headers(tenant_id))
    assert r.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_revoke_all_for_user(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    await _create(client, tenant_id, user_id)
    await _create(client, tenant_id, user_id)
    r = await client.post(
        "/api/v1/sessions/revoke-all",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["revoked"] == 2


@pytest.mark.asyncio
async def test_user_sessions_list_and_delete(client: AsyncClient) -> None:
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()
    await _create(client, tenant_id, user_id)
    await _create(client, tenant_id, user_id)

    r = await client.get(
        f"/api/v1/users/{user_id}/sessions", headers=_headers(tenant_id)
    )
    assert r.json()["total"] == 2

    r = await client.delete(
        f"/api/v1/users/{user_id}/sessions", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["revoked"] == 2


@pytest.mark.asyncio
async def test_cross_tenant_isolation(client: AsyncClient) -> None:
    owner_tenant, user_id = uuid.uuid4(), uuid.uuid4()
    created = await _create(client, owner_tenant, user_id)
    sid = created["session"]["id"]

    other_tenant = uuid.uuid4()
    r = await client.get(f"/api/v1/sessions/{sid}", headers=_headers(other_tenant))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tenant_header_required(client: AsyncClient) -> None:
    r = await client.post("/api/v1/sessions", json={"user_id": str(uuid.uuid4())})
    assert r.status_code == 400
