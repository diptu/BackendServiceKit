"""Avatar set/get/delete."""

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
async def test_get_avatar_no_row_yet_returns_defaults(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}/avatar", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["url"] is None


@pytest.mark.asyncio
async def test_set_avatar(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={
            "url": "https://cdn.example.com/avatars/a.png",
            "content_type": "image/png",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["url"] == "https://cdn.example.com/avatars/a.png"
    assert body["content_type"] == "image/png"
    assert body["uploaded_at"] is not None


@pytest.mark.asyncio
async def test_set_avatar_unknown_user_404s(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={"url": "https://cdn.example.com/a.png"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_avatar(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={"url": "https://cdn.example.com/a.png"},
        headers=_headers(tenant_id),
    )
    r = await client.delete(
        f"/api/v1/profiles/{user_id}/avatar", headers=_headers(tenant_id)
    )
    assert r.status_code == 204

    get_r = await client.get(
        f"/api/v1/profiles/{user_id}/avatar", headers=_headers(tenant_id)
    )
    assert get_r.json()["url"] is None


@pytest.mark.asyncio
async def test_delete_avatar_cross_tenant_does_not_delete_other_tenants_avatar(
    client: AsyncClient,
) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)
    await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={"url": "https://cdn.example.com/a.png"},
        headers=_headers(owner_tenant_id),
    )

    other_tenant_id = uuid.uuid4()
    r = await client.delete(
        f"/api/v1/profiles/{user_id}/avatar", headers=_headers(other_tenant_id)
    )
    assert r.status_code == 204

    get_r = await client.get(
        f"/api/v1/profiles/{user_id}/avatar", headers=_headers(owner_tenant_id)
    )
    assert get_r.json()["url"] == "https://cdn.example.com/a.png"


@pytest.mark.asyncio
async def test_get_avatar_cross_tenant_returns_defaults_not_other_tenants_avatar(
    client: AsyncClient,
) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)
    await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={"url": "https://cdn.example.com/a.png"},
        headers=_headers(owner_tenant_id),
    )

    other_tenant_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}/avatar", headers=_headers(other_tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["url"] is None


@pytest.mark.asyncio
async def test_replace_avatar(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={"url": "https://cdn.example.com/old.png"},
        headers=_headers(tenant_id),
    )
    r = await client.post(
        f"/api/v1/profiles/{user_id}/avatar",
        json={"url": "https://cdn.example.com/new.png"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["url"] == "https://cdn.example.com/new.png"
