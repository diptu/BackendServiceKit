"""Platform invitation create/accept/revoke, replay prevention, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


@pytest.mark.asyncio
async def test_create_invitation_returns_raw_token_once(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    inviter = uuid.uuid4()

    r = await client.post(
        "/api/v1/platform-invitations",
        json={"email": "new-hire@example.com", "invited_by": str(inviter)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert isinstance(data["token"], str) and len(data["token"]) > 20


@pytest.mark.asyncio
async def test_accept_invitation_creates_user(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    inviter = uuid.uuid4()

    r = await client.post(
        "/api/v1/platform-invitations",
        json={"email": "invitee@example.com", "invited_by": str(inviter)},
        headers=_headers(tenant_id),
    )
    token = r.json()["token"]

    r2 = await client.post(
        "/api/v1/platform-invitations/accept",
        json={"token": token, "first_name": "New", "last_name": "Hire"},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["email"] == "invitee@example.com"
    assert data["display_name"] == "New Hire"
    assert data["status"] == "pending"

    users = await client.get("/api/v1/users", headers=_headers(tenant_id))
    assert users.json()["total"] == 1


@pytest.mark.asyncio
async def test_accept_invitation_replay_prevented(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    inviter = uuid.uuid4()

    r = await client.post(
        "/api/v1/platform-invitations",
        json={"email": "invitee@example.com", "invited_by": str(inviter)},
        headers=_headers(tenant_id),
    )
    token = r.json()["token"]

    r2 = await client.post(
        "/api/v1/platform-invitations/accept",
        json={"token": token, "first_name": "New", "last_name": "Hire"},
    )
    assert r2.status_code == 200

    r3 = await client.post(
        "/api/v1/platform-invitations/accept",
        json={"token": token, "first_name": "Someone", "last_name": "Else"},
    )
    assert r3.status_code == 409


@pytest.mark.asyncio
async def test_accept_invitation_unknown_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/platform-invitations/accept",
        json={"token": "not-a-real-token", "first_name": "A", "last_name": "B"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_invitations(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post(
        "/api/v1/platform-invitations",
        json={"email": "a@example.com", "invited_by": str(uuid.uuid4())},
        headers=_headers(tenant_id),
    )

    r = await client.get("/api/v1/platform-invitations", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert "token" not in r.json()["items"][0]


@pytest.mark.asyncio
async def test_revoke_invitation(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    invite = await client.post(
        "/api/v1/platform-invitations",
        json={"email": "a@example.com", "invited_by": str(uuid.uuid4())},
        headers=_headers(tenant_id),
    )
    invitation_id = invite.json()["id"]
    token = invite.json()["token"]

    r = await client.post(
        f"/api/v1/platform-invitations/{invitation_id}/revoke",
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"

    accept = await client.post(
        "/api/v1/platform-invitations/accept",
        json={"token": token, "first_name": "A", "last_name": "B"},
    )
    assert accept.status_code == 409


@pytest.mark.asyncio
async def test_revoke_invitation_not_found(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/platform-invitations/{uuid.uuid4()}/revoke",
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404
