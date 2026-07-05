"""Entitlement CRUD, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


@pytest.mark.asyncio
async def test_create_entitlement(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/entitlements",
        json={"user_id": str(user_id), "key": "seats", "value": 5},
        headers=_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "active"
    assert data["value"] == 5


@pytest.mark.asyncio
async def test_get_entitlement_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/entitlements",
        json={"user_id": str(user_id), "key": "seats", "value": 5},
        headers=_headers(),
    )
    entitlement_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/entitlements/{entitlement_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_entitlements(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await client.post(
        "/api/v1/entitlements",
        json={"user_id": str(user_id), "key": "seats", "value": 5},
        headers=_headers(tenant_id),
    )

    r = await client.get("/api/v1/entitlements", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_delete_entitlement(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/entitlements",
        json={"user_id": str(user_id), "key": "seats", "value": 5},
        headers=_headers(tenant_id),
    )
    entitlement_id = r.json()["id"]

    r2 = await client.delete(
        f"/api/v1/entitlements/{entitlement_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 204

    r3 = await client.get(
        f"/api/v1/entitlements/{entitlement_id}", headers=_headers(tenant_id)
    )
    assert r3.status_code == 404
