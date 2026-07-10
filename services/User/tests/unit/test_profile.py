"""Profile CRUD, default-valued reads, existence-check gating.

Simplified from UserProfileManagement's original version: that service
needed a FakeUserProfileClient standing in for a separate UserManagement
service. Now it's the same service, so tests just create a real user via
/api/v1/users and operate on that same user_id directly.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


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
async def test_get_profile_no_row_yet_returns_defaults_not_404(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.get(f"/api/v1/profiles/{user_id}", headers=_headers(tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] is None
    assert body["created_at"] is None


@pytest.mark.asyncio
async def test_get_profile_cross_tenant_returns_defaults_not_other_tenants_data(
    client: AsyncClient,
) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)
    await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "Secret bio"},
        headers=_headers(owner_tenant_id),
    )

    other_tenant_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}", headers=_headers(other_tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["bio"] is None


@pytest.mark.asyncio
async def test_update_profile_cross_tenant_404s(client: AsyncClient) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)

    other_tenant_id = uuid.uuid4()
    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "Hijacked bio"},
        headers=_headers(other_tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_profile_unknown_user_404s(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "hello"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_profile_known_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "Backend engineer", "pronouns": "she/her"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] == "Backend engineer"
    assert body["pronouns"] == "she/her"
    assert body["created_at"] is not None


@pytest.mark.asyncio
async def test_update_profile_partial_update_preserves_other_fields(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "Bio one"},
        headers=_headers(tenant_id),
    )
    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"pronouns": "they/them"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] == "Bio one"
    assert body["pronouns"] == "they/them"
