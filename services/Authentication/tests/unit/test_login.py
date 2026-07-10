"""Login: success, generic failure messaging, account lockout, tenant isolation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery-staple"


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


async def _create_credential(
    client: AsyncClient, tenant_id: uuid.UUID, email: str = "ada@example.com"
) -> uuid.UUID:
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/credentials",
        json={"user_id": str(user_id), "email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204
    return user_id


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await _create_credential(client, tenant_id)

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900


@pytest.mark.asyncio
async def test_login_wrong_password_generic_401(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await _create_credential(client, tenant_id)

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "wrong-password"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 401
    wrong_detail = r.json()["detail"]

    r2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 401
    # Same message whether the email is unknown or the password is wrong —
    # no enumeration signal.
    assert r2.json()["detail"] == wrong_detail


@pytest.mark.asyncio
async def test_login_cross_tenant_fails(client: AsyncClient) -> None:
    owner_tenant_id = uuid.uuid4()
    await _create_credential(client, owner_tenant_id, email="scoped@example.com")

    other_tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "scoped@example.com", "password": PASSWORD},
        headers=_headers(other_tenant_id),
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_account_locks_after_max_failed_attempts(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await _create_credential(client, tenant_id, email="lockout@example.com")

    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "lockout@example.com", "password": "wrong"},
            headers=_headers(tenant_id),
        )
        assert r.status_code == 401

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "lockout@example.com", "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 423
