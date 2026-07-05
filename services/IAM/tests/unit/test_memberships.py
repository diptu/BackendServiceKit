"""Tenant Membership CRUD — tenant_id comes from the URL path, not a header."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_tenant_member(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    r = await client.post(
        f"/api/v1/tenant-memberships/{tenant_id}/members",
        json={"user_id": str(user_id)},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["user_id"] == str(user_id)
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_add_tenant_member_already_exists(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    r1 = await client.post(
        f"/api/v1/tenant-memberships/{tenant_id}/members",
        json={"user_id": str(user_id)},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/tenant-memberships/{tenant_id}/members",
        json={"user_id": str(user_id)},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_tenant_members(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await client.post(
        f"/api/v1/tenant-memberships/{tenant_id}/members",
        json={"user_id": str(user_id)},
    )

    r = await client.get(f"/api/v1/tenant-memberships/{tenant_id}/members")
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_remove_tenant_member(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await client.post(
        f"/api/v1/tenant-memberships/{tenant_id}/members",
        json={"user_id": str(user_id)},
    )

    r = await client.delete(f"/api/v1/tenant-memberships/{tenant_id}/members/{user_id}")
    assert r.status_code == 204

    r2 = await client.delete(
        f"/api/v1/tenant-memberships/{tenant_id}/members/{user_id}"
    )
    assert r2.status_code == 404
