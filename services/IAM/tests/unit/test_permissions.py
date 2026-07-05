"""Permission CRUD and tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"perm-{uuid.uuid4().hex[:8]}:read"}
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_permission(client: AsyncClient) -> None:
    r = await client.post("/api/v1/permissions", json=_payload(), headers=_headers())
    assert r.status_code == 201
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_create_permission_duplicate_name_same_tenant(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    name = f"dup-{uuid.uuid4().hex[:8]}:read"
    r1 = await client.post(
        "/api/v1/permissions", json=_payload(name=name), headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/permissions", json=_payload(name=name), headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_permission_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    r = await client.post("/api/v1/permissions", json=_payload(), headers=_headers())
    permission_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/permissions/{permission_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_permissions(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post(
        "/api/v1/permissions", json=_payload(), headers=_headers(tenant_id)
    )
    r = await client.get("/api/v1/permissions", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_permission(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/permissions", json=_payload(), headers=_headers(tenant_id)
    )
    permission_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/permissions/{permission_id}",
        json={"description": "updated"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["description"] == "updated"


@pytest.mark.asyncio
async def test_delete_permission(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/permissions", json=_payload(), headers=_headers(tenant_id)
    )
    permission_id = r.json()["id"]

    r2 = await client.delete(
        f"/api/v1/permissions/{permission_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 204

    r3 = await client.get(
        f"/api/v1/permissions/{permission_id}", headers=_headers(tenant_id)
    )
    assert r3.status_code == 404
