"""Refresh token rotation and replay detection."""

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
    assert r.status_code == 200
    result: dict[str, str] = r.json()
    return result


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "refresh@example.com")

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    new_tokens = r.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"] != tokens["access_token"]


@pytest.mark.asyncio
async def test_refresh_reuse_of_rotated_token_is_rejected(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "reuse@example.com")

    r1 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r1.status_code == 200

    # Reusing the now-rotated (revoked) refresh token must fail — replay
    # detection revokes the whole chain, so even the fresh token from r1 is
    # no longer valid.
    r2 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 401

    r3 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": r1.json()["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_refresh_unknown_token_401s(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 401
