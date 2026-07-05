"""User Attribute CRUD (ABAC key/value data), tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


@pytest.mark.asyncio
async def test_create_attribute(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/users/{user_id}/attributes",
        json={"key": "department", "value": "engineering", "value_type": "string"},
        headers=_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["key"] == "department"
    assert data["value"] == "engineering"


@pytest.mark.asyncio
async def test_create_attribute_duplicate_key_same_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    body = {"key": "region", "value": "us-east", "value_type": "string"}

    r1 = await client.post(
        f"/api/v1/users/{user_id}/attributes", json=body, headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/users/{user_id}/attributes", json=body, headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_attributes(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await client.post(
        f"/api/v1/users/{user_id}/attributes",
        json={"key": "clearance", "value": "high", "value_type": "string"},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/users/{user_id}/attributes", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_update_attribute(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/users/{user_id}/attributes",
        json={"key": "level", "value": 1, "value_type": "number"},
        headers=_headers(tenant_id),
    )
    attribute_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/users/{user_id}/attributes/{attribute_id}",
        json={"value": 2},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["value"] == 2


@pytest.mark.asyncio
async def test_delete_attribute(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/users/{user_id}/attributes",
        json={"key": "temp", "value": "x", "value_type": "string"},
        headers=_headers(tenant_id),
    )
    attribute_id = r.json()["id"]

    r2 = await client.delete(
        f"/api/v1/users/{user_id}/attributes/{attribute_id}",
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 204

    r3 = await client.get(
        f"/api/v1/users/{user_id}/attributes", headers=_headers(tenant_id)
    )
    assert r3.json()["total"] == 0
