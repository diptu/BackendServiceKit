"""Organization membership CRUD, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


async def _create_org(client: AsyncClient, tenant_id: uuid.UUID) -> str:
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme", "slug": f"acme-{uuid.uuid4().hex[:8]}"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    return str(r.json()["id"])


@pytest.mark.asyncio
async def test_add_member(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    user_id = uuid.uuid4()

    r = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(user_id), "role": "admin"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == str(user_id)
    assert data["role"] == "admin"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_add_member_already_exists(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    user_id = uuid.uuid4()

    r1 = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_members(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(uuid.uuid4())},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/organizations/{org_id}/members", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_update_member_role(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    user_id = uuid.uuid4()
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )

    r = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{user_id}",
        json={"role": "owner"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "owner"


@pytest.mark.asyncio
async def test_update_member_role_not_found(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{uuid.uuid4()}",
        json={"role": "owner"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_remove_member(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    user_id = uuid.uuid4()
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )

    r = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{user_id}", headers=_headers(tenant_id)
    )
    assert r.status_code == 204

    r2 = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{user_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 404
