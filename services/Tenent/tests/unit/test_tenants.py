"""Tenant CRUD and lifecycle transition tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": f"test-tenant-{uuid.uuid4().hex[:8]}",
        "display_name": "Test Tenant",
        "region": "us-east-1",
        "owner_id": str(uuid.uuid4()),
    }
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_tenant(client: AsyncClient) -> None:
    r = await client.post("/api/v1/tenants", json=_payload())
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_tenant_duplicate_name(client: AsyncClient) -> None:
    name = f"dup-{uuid.uuid4().hex[:8]}"
    r1 = await client.post("/api/v1/tenants", json=_payload(name=name))
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/tenants", json=_payload(name=name))
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_tenant(client: AsyncClient) -> None:
    r = await client.post("/api/v1/tenants", json=_payload())
    tenant_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/tenants/{tenant_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == tenant_id


@pytest.mark.asyncio
async def test_get_tenant_not_found(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/tenants/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_tenants(client: AsyncClient) -> None:
    await client.post("/api/v1/tenants", json=_payload())
    r = await client.get("/api/v1/tenants")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_update_tenant(client: AsyncClient) -> None:
    r = await client.post("/api/v1/tenants", json=_payload())
    tenant_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/tenants/{tenant_id}", json={"display_name": "Updated Name"}
    )
    assert r2.status_code == 200
    assert r2.json()["display_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_lifecycle_transitions(client: AsyncClient) -> None:
    """Draft → provisioning → pending → active → suspended."""
    r = await client.post("/api/v1/tenants", json=_payload())
    assert r.status_code == 201
    tenant_id = r.json()["id"]

    r2 = await client.put(f"/api/v1/tenants/{tenant_id}/provision")
    assert r2.status_code == 200
    assert r2.json()["status"] == "provisioning"

    r3 = await client.put(f"/api/v1/tenants/{tenant_id}/pend")
    assert r3.status_code == 200
    assert r3.json()["status"] == "pending"

    r4 = await client.put(f"/api/v1/tenants/{tenant_id}/activate")
    assert r4.status_code == 200
    assert r4.json()["status"] == "active"

    r5 = await client.put(f"/api/v1/tenants/{tenant_id}/suspend")
    assert r5.status_code == 200
    assert r5.json()["status"] == "suspended"


@pytest.mark.asyncio
async def test_invalid_transition(client: AsyncClient) -> None:
    r = await client.post("/api/v1/tenants", json=_payload())
    tenant_id = r.json()["id"]
    # draft → activate is invalid
    r2 = await client.put(f"/api/v1/tenants/{tenant_id}/activate")
    assert r2.status_code in {409, 422}


@pytest.mark.asyncio
async def test_owner_management(client: AsyncClient) -> None:
    owner_id = str(uuid.uuid4())
    r = await client.post("/api/v1/tenants", json=_payload(owner_id=owner_id))
    tenant_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/tenants/{tenant_id}/owners")
    assert r2.status_code == 200
    assert r2.json()["total"] == 1

    new_user = str(uuid.uuid4())
    r3 = await client.post(
        f"/api/v1/tenants/{tenant_id}/owners",
        json={"user_id": new_user, "role": "admin"},
    )
    assert r3.status_code == 201

    r4 = await client.get(f"/api/v1/tenants/{tenant_id}/owners")
    assert r4.json()["total"] == 2


@pytest.mark.asyncio
async def test_metadata_update(client: AsyncClient) -> None:
    r = await client.post("/api/v1/tenants", json=_payload())
    tenant_id = r.json()["id"]

    r2 = await client.put(
        f"/api/v1/tenants/{tenant_id}/metadata",
        json={"metadata": {"env": "test", "tier": "free"}},
    )
    assert r2.status_code == 200
    entries = {e["key"]: e["value"] for e in r2.json()["entries"]}
    assert entries["env"] == "test"
    assert entries["tier"] == "free"
