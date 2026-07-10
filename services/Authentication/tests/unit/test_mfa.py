"""MFA (TOTP): enrollment, activation, login step-up, recovery codes, disable."""

from __future__ import annotations

import uuid

import pyotp
import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery-staple"


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


def _auth_headers(tenant_id: uuid.UUID, access_token: str) -> dict[str, str]:
    return {
        "X-Tenant-ID": str(tenant_id),
        "Authorization": f"Bearer {access_token}",
    }


async def _create_and_login(
    client: AsyncClient, tenant_id: uuid.UUID, email: str
) -> str:
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/credentials",
        json={"user_id": str(user_id), "email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    return str(r.json()["access_token"])


async def _enroll_mfa(
    client: AsyncClient, tenant_id: uuid.UUID, access_token: str
) -> tuple[str, list[str]]:
    r = await client.post(
        "/api/v1/auth/mfa/setup", headers=_auth_headers(tenant_id, access_token)
    )
    assert r.status_code == 200
    body = r.json()
    secret = str(body["secret"])
    recovery_codes = [str(c) for c in body["recovery_codes"]]

    code = pyotp.TOTP(secret).now()
    r = await client.post(
        "/api/v1/auth/mfa/activate",
        json={"code": code},
        headers=_auth_headers(tenant_id, access_token),
    )
    assert r.status_code == 204
    return secret, recovery_codes


@pytest.mark.asyncio
async def test_setup_returns_secret_and_recovery_codes(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa1@example.com")
    r = await client.post(
        "/api/v1/auth/mfa/setup", headers=_auth_headers(tenant_id, token)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["secret"]
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert len(body["recovery_codes"]) == 10


@pytest.mark.asyncio
async def test_activate_with_wrong_code_rejected(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa2@example.com")
    await client.post("/api/v1/auth/mfa/setup", headers=_auth_headers(tenant_id, token))
    r = await client.post(
        "/api/v1/auth/mfa/activate",
        json={"code": "000000"},
        headers=_auth_headers(tenant_id, token),
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_with_mfa_requires_step_up(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa3@example.com")
    secret, _ = await _enroll_mfa(client, tenant_id, token)

    # Login now returns a challenge, not tokens.
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfa3@example.com", "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert body["access_token"] is None

    # Redeem the challenge with a valid TOTP code → real tokens.
    r = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": body["mfa_token"], "code": pyotp.TOTP(secret).now()},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["refresh_token"]


@pytest.mark.asyncio
async def test_step_up_with_wrong_code_rejected(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa4@example.com")
    await _enroll_mfa(client, tenant_id, token)

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfa4@example.com", "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    mfa_token = r.json()["mfa_token"]
    r = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": "000000"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_recovery_code_is_single_use(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa5@example.com")
    _, recovery_codes = await _enroll_mfa(client, tenant_id, token)
    recovery = recovery_codes[0]

    async def _step_up_with(code: str) -> int:
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "mfa5@example.com", "password": PASSWORD},
            headers=_headers(tenant_id),
        )
        mfa_token = r.json()["mfa_token"]
        r = await client.post(
            "/api/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": code},
            headers=_headers(tenant_id),
        )
        return r.status_code

    assert await _step_up_with(recovery) == 200
    # Same recovery code a second time is rejected.
    assert await _step_up_with(recovery) == 401


@pytest.mark.asyncio
async def test_disable_restores_plain_login(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa6@example.com")
    secret, _ = await _enroll_mfa(client, tenant_id, token)

    r = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"code": pyotp.TOTP(secret).now()},
        headers=_auth_headers(tenant_id, token),
    )
    assert r.status_code == 204

    # Login returns tokens directly again.
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfa6@example.com", "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["mfa_required"] is False
    assert r.json()["access_token"]


@pytest.mark.asyncio
async def test_setup_when_already_enabled_conflicts(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _create_and_login(client, tenant_id, "mfa7@example.com")
    await _enroll_mfa(client, tenant_id, token)
    r = await client.post(
        "/api/v1/auth/mfa/setup", headers=_auth_headers(tenant_id, token)
    )
    assert r.status_code == 409
