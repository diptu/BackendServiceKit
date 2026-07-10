"""Preferences: locale/timezone/extra, defaults, independence from other resources."""

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
async def test_get_preferences_no_row_yet_returns_defaults(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}/preferences", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "en"
    assert body["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_update_preferences(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    r = await client.patch(
        f"/api/v1/profiles/{user_id}/preferences",
        json={"locale": "bn", "timezone": "Asia/Dhaka", "extra": {"newsletter": False}},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "bn"
    assert body["timezone"] == "Asia/Dhaka"
    assert body["extra"] == {"newsletter": False}


@pytest.mark.asyncio
async def test_get_preferences_cross_tenant_returns_defaults(
    client: AsyncClient,
) -> None:
    owner_tenant_id = uuid.uuid4()
    user_id = await _create_user(client, owner_tenant_id)
    await client.patch(
        f"/api/v1/profiles/{user_id}/preferences",
        json={"locale": "bn"},
        headers=_headers(owner_tenant_id),
    )

    other_tenant_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/profiles/{user_id}/preferences", headers=_headers(other_tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["locale"] == "en"


@pytest.mark.asyncio
async def test_updating_preferences_does_not_create_profile_row(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = await _create_user(client, tenant_id)

    await client.patch(
        f"/api/v1/profiles/{user_id}/preferences",
        json={"locale": "fr"},
        headers=_headers(tenant_id),
    )
    profile = await client.get(
        f"/api/v1/profiles/{user_id}", headers=_headers(tenant_id)
    )
    assert profile.json()["created_at"] is None
