"""Contact info: phone/secondary_email/address."""

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
async def test_get_contacts_no_row_yet_returns_defaults(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}/contacts", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["phone"] is None


@pytest.mark.asyncio
async def test_update_contacts(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.patch(
        f"/api/v1/profiles/{user_id}/contacts",
        json={
            "phone": "+8801700000000",
            "secondary_email": "backup@example.com",
            "address": {"city": "Dhaka", "country": "BD"},
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["phone"] == "+8801700000000"
    assert body["secondary_email"] == "backup@example.com"
    assert body["address"] == {"city": "Dhaka", "country": "BD"}


@pytest.mark.asyncio
async def test_get_contacts_cross_tenant_returns_defaults(client: AsyncClient) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)
    await client.patch(
        f"/api/v1/profiles/{user_id}/contacts",
        json={"phone": "+8801700000000"},
        headers=_headers(owner_tenant_id),
    )

    other_tenant_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}/contacts", headers=_headers(other_tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["phone"] is None


@pytest.mark.asyncio
async def test_update_contacts_cross_tenant_404s(client: AsyncClient) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)

    other_tenant_id = uuid.uuid4()
    r = await client.patch(
        f"/api/v1/profiles/{user_id}/contacts",
        json={"phone": "+19999999999"},
        headers=_headers(other_tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_contacts_unknown_user_404s(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.patch(
        f"/api/v1/profiles/{user_id}/contacts",
        json={"phone": "+1234567890"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404
