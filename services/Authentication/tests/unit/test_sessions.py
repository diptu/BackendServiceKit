"""Session listing and revocation."""

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
async def test_list_sessions(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "sessions@example.com")

    r = await client.get(
        "/api/v1/auth/sessions",
        headers={
            **_headers(tenant_id),
            "Authorization": f"Bearer {tokens['access_token']}",
        },
    )
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


@pytest.mark.asyncio
async def test_revoke_own_session(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    tokens = await _login(client, tenant_id, "revoke-own@example.com")
    auth_headers = {
        **_headers(tenant_id),
        "Authorization": f"Bearer {tokens['access_token']}",
    }

    sessions = (await client.get("/api/v1/auth/sessions", headers=auth_headers)).json()
    session_id = sessions["items"][0]["id"]

    r = await client.delete(f"/api/v1/auth/sessions/{session_id}", headers=auth_headers)
    assert r.status_code == 204

    refresh_r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert refresh_r.status_code == 401


@pytest.mark.asyncio
async def test_cannot_revoke_another_users_session(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    victim_tokens = await _login(client, tenant_id, "victim@example.com")
    attacker_tokens = await _login(client, tenant_id, "attacker@example.com")

    victim_headers = {
        **_headers(tenant_id),
        "Authorization": f"Bearer {victim_tokens['access_token']}",
    }
    attacker_headers = {
        **_headers(tenant_id),
        "Authorization": f"Bearer {attacker_tokens['access_token']}",
    }

    victim_sessions = (
        await client.get("/api/v1/auth/sessions", headers=victim_headers)
    ).json()
    victim_session_id = victim_sessions["items"][0]["id"]

    # Attacker tries to revoke the victim's session_id using their own token.
    r = await client.delete(
        f"/api/v1/auth/sessions/{victim_session_id}", headers=attacker_headers
    )
    assert r.status_code == 204  # no-op, not found-for-this-user — not a leak

    # Victim's session is still alive.
    refresh_r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": victim_tokens["refresh_token"]},
        headers=_headers(tenant_id),
    )
    assert refresh_r.status_code == 200
