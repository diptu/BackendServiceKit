"""Role CRUD, role<->permission linkage, user<->role assignment, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _role_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"role-{uuid.uuid4().hex[:8]}"}
    base.update(kwargs)
    return base


def _permission_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"perm-{uuid.uuid4().hex[:8]}:read"}
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_role(client: AsyncClient) -> None:
    r = await client.post("/api/v1/roles", json=_role_payload(), headers=_headers())
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_role_requires_tenant_header(client: AsyncClient) -> None:
    r = await client.post("/api/v1/roles", json=_role_payload())
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_role_duplicate_name_same_tenant(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    name = f"dup-{uuid.uuid4().hex[:8]}"
    r1 = await client.post(
        "/api/v1/roles", json=_role_payload(name=name), headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/roles", json=_role_payload(name=name), headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_role_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    r = await client.post("/api/v1/roles", json=_role_payload(), headers=_headers())
    role_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/roles/{role_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_roles(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post(
        "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
    )
    r = await client.get("/api/v1/roles", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_role(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
    )
    role_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"name": "updated-role"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "updated-role"


@pytest.mark.asyncio
async def test_delete_role(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
    )
    role_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/roles/{role_id}", headers=_headers(tenant_id))
    assert r2.status_code == 204

    r3 = await client.get(f"/api/v1/roles/{role_id}", headers=_headers(tenant_id))
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_role_permission_linkage(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]
    permission_id = (
        await client.post(
            "/api/v1/permissions",
            json=_permission_payload(),
            headers=_headers(tenant_id),
        )
    ).json()["id"]

    r = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204

    r2 = await client.get(
        f"/api/v1/roles/{role_id}/permissions", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["total"] == 1

    r3 = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=_headers(tenant_id),
    )
    assert r3.status_code == 409

    r4 = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{permission_id}",
        headers=_headers(tenant_id),
    )
    assert r4.status_code == 204

    r5 = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{permission_id}",
        headers=_headers(tenant_id),
    )
    assert r5.status_code == 404


@pytest.mark.asyncio
async def test_user_role_assignment(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]

    r = await client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": role_id},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/users/{user_id}/roles", headers=_headers(tenant_id))
    assert r2.status_code == 200
    assert r2.json()["total"] == 1

    r3 = await client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": role_id},
        headers=_headers(tenant_id),
    )
    assert r3.status_code == 409

    r4 = await client.delete(
        f"/api/v1/users/{user_id}/roles/{role_id}", headers=_headers(tenant_id)
    )
    assert r4.status_code == 204

    r5 = await client.delete(
        f"/api/v1/users/{user_id}/roles/{role_id}", headers=_headers(tenant_id)
    )
    assert r5.status_code == 404
