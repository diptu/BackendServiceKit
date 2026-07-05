"""User CRUD, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient) -> None:
    r = await client.post("/api/v1/users", json=_payload(), headers=_headers())
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["display_name"] == "Ada Lovelace"


@pytest.mark.asyncio
async def test_create_user_requires_tenant_header(client: AsyncClient) -> None:
    r = await client.post("/api/v1/users", json=_payload())
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_user_duplicate_email_same_tenant(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    r1 = await client.post(
        "/api/v1/users", json=_payload(email=email), headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/users", json=_payload(email=email), headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_user_same_email_different_tenant_allowed(
    client: AsyncClient,
) -> None:
    email = f"shared-{uuid.uuid4().hex[:8]}@example.com"
    r1 = await client.post(
        "/api/v1/users", json=_payload(email=email), headers=_headers()
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/users", json=_payload(email=email), headers=_headers()
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_get_user_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    r = await client.post("/api/v1/users", json=_payload(), headers=_headers())
    user_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/users/{user_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post("/api/v1/users", json=_payload(), headers=_headers(tenant_id))
    r = await client.get("/api/v1/users", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post("/api/v1/users", json=_payload(), headers=_headers(tenant_id))
    user_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"first_name": "Grace"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["first_name"] == "Grace"
    assert r2.json()["display_name"] == "Grace Lovelace"


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post("/api/v1/users", json=_payload(), headers=_headers(tenant_id))
    user_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/users/{user_id}", headers=_headers(tenant_id))
    assert r2.status_code == 204

    r3 = await client.get(f"/api/v1/users/{user_id}", headers=_headers(tenant_id))
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_restore_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post("/api/v1/users", json=_payload(), headers=_headers(tenant_id))
    user_id = r.json()["id"]
    await client.delete(f"/api/v1/users/{user_id}", headers=_headers(tenant_id))

    r2 = await client.post(
        f"/api/v1/users/{user_id}/restore", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["deleted_at"] is None

    r3 = await client.get(f"/api/v1/users/{user_id}", headers=_headers(tenant_id))
    assert r3.status_code == 200


@pytest.mark.asyncio
async def test_restore_user_not_deleted(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post("/api/v1/users", json=_payload(), headers=_headers(tenant_id))
    user_id = r.json()["id"]

    r2 = await client.post(
        f"/api/v1/users/{user_id}/restore", headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_restore_user_not_found(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/users/{uuid.uuid4()}/restore", headers=_headers(tenant_id)
    )
    assert r.status_code == 404
