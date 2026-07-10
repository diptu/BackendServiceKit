"""Logout / revoke."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery-staple"


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


async def _login(
    client: AsyncClient, tenant_id: uuid.UUID, email: str
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/credentials",
        json={"user_id": str(uuid.uuid4()), "email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    result: dict[str, str] = r.json()
    return result


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "logout@example.com")

    r = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204

    r2 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_logout_is_idempotent(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "idempotent@example.com")

    r1 = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r1.status_code == 204

    r2 = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_logout_all_revokes_every_session(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    email = "multi-device@example.com"
    tokens_a = await _login(client, tenant_id, email)

    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    tokens_b = login_r.json()

    r = await client.post(
        "/api/v1/auth/logout-all",
        headers={
            **_headers(tenant_id),
            "Authorization": f"Bearer {tokens_a['access_token']}",
        },
    )
    assert r.status_code == 204

    for tokens in (tokens_a, tokens_b):
        refresh_r = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers=_headers(tenant_id),
        )
        assert refresh_r.status_code == 401
