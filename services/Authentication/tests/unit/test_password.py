"""Change-password (authenticated) and forgot/reset password flows."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery-staple"
NEW_PASSWORD = "another-strong-password-2"


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
async def test_change_password_success_and_revokes_sessions(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    email = "change@example.com"
    tokens = await _login(client, tenant_id, email)

    r = await client.post(
        "/api/v1/auth/password/change",
        json={"old_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers={
            **_headers(tenant_id),
            "Authorization": f"Bearer {tokens['access_token']}",
        },
    )
    assert r.status_code == 204

    # Old sessions are revoked by a password change.
    refresh_r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert refresh_r.status_code == 401

    # New password logs in; old one no longer works.
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": NEW_PASSWORD},
        headers=_headers(tenant_id),
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old_password_401s(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "wrongold@example.com")

    r = await client.post(
        "/api/v1/auth/password/change",
        json={"old_password": "not-the-password", "new_password": NEW_PASSWORD},
        headers={
            **_headers(tenant_id),
            "Authorization": f"Bearer {tokens['access_token']}",
        },
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_change_password_requires_bearer_token(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/password/change",
        json={"old_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_returns_generic_response_for_unknown_email(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "nobody@example.com"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["reset_token"] is None


@pytest.mark.asyncio
async def test_forgot_then_reset_password_flow(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    email = "forgot@example.com"
    await _login(client, tenant_id, email)

    forgot_r = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
        headers=_headers(tenant_id),
    )
    assert forgot_r.status_code == 200
    reset_token = forgot_r.json()["reset_token"]
    assert reset_token is not None

    reset_r = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": NEW_PASSWORD},
        headers=_headers(tenant_id),
    )
    assert reset_r.status_code == 204

    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": NEW_PASSWORD},
        headers=_headers(tenant_id),
    )
    assert login_r.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_rejects_reused_token(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    email = "reuse-reset@example.com"
    await _login(client, tenant_id, email)

    forgot_r = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
        headers=_headers(tenant_id),
    )
    reset_token = forgot_r.json()["reset_token"]

    r1 = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": NEW_PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r1.status_code == 204

    r2 = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": "yet-another-password-3"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 400
