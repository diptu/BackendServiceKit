"""Token introspection — RFC 7662 style: always 200, active:false for invalid."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery-staple"


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_introspect_valid_token(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    await client.post(
        "/api/v1/auth/credentials",
        json={
            "user_id": user_id,
            "email": "introspect@example.com",
            "password": PASSWORD,
        },
        headers=_headers(tenant_id),
    )
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": "introspect@example.com", "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    access_token = login_r.json()["access_token"]

    r = await client.post("/api/v1/auth/introspect", json={"token": access_token})
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True
    assert body["tenant_id"] == str(tenant_id)
    assert body["user_id"] == user_id


@pytest.mark.asyncio
async def test_introspect_garbage_token_is_inactive_not_an_error(
    client: AsyncClient,
) -> None:
    r = await client.post("/api/v1/auth/introspect", json={"token": "not-a-real-jwt"})
    assert r.status_code == 200
    assert r.json()["active"] is False
