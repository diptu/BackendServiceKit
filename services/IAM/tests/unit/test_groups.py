"""Group CRUD, group<->user membership, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"group-{uuid.uuid4().hex[:8]}"}
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_group(client: AsyncClient) -> None:
    r = await client.post("/api/v1/groups", json=_payload(), headers=_headers())
    assert r.status_code == 201
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_create_group_duplicate_name_same_tenant(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    name = f"dup-{uuid.uuid4().hex[:8]}"
    r1 = await client.post(
        "/api/v1/groups", json=_payload(name=name), headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/groups", json=_payload(name=name), headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_group_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    r = await client.post("/api/v1/groups", json=_payload(), headers=_headers())
    group_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/groups/{group_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_update_group(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/groups", json=_payload(), headers=_headers(tenant_id)
    )
    group_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/groups/{group_id}",
        json={"name": "updated-group"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "updated-group"


@pytest.mark.asyncio
async def test_delete_group(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/groups", json=_payload(), headers=_headers(tenant_id)
    )
    group_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/groups/{group_id}", headers=_headers(tenant_id))
    assert r2.status_code == 204

    r3 = await client.get(f"/api/v1/groups/{group_id}", headers=_headers(tenant_id))
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_group_membership(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    group_id = (
        await client.post(
            "/api/v1/groups", json=_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]

    r = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204

    r2 = await client.get(
        f"/api/v1/groups/{group_id}/members", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["total"] == 1
    assert r2.json()["items"] == [str(user_id)]

    r3 = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r3.status_code == 409

    r4 = await client.delete(
        f"/api/v1/groups/{group_id}/members/{user_id}", headers=_headers(tenant_id)
    )
    assert r4.status_code == 204

    r5 = await client.delete(
        f"/api/v1/groups/{group_id}/members/{user_id}", headers=_headers(tenant_id)
    )
    assert r5.status_code == 404
