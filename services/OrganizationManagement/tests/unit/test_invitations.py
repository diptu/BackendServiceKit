"""Invitation create/accept/revoke, replay prevention, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


async def _create_org(client: AsyncClient, tenant_id: uuid.UUID) -> str:
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme", "slug": f"acme-{uuid.uuid4().hex[:8]}"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    return str(r.json()["id"])


@pytest.mark.asyncio
async def test_create_invitation_returns_raw_token_once(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    inviter = uuid.uuid4()

    r = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "new-hire@example.com", "invited_by": str(inviter)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert isinstance(data["token"], str) and len(data["token"]) > 20


@pytest.mark.asyncio
async def test_accept_invitation(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    inviter = uuid.uuid4()
    invitee = uuid.uuid4()

    r = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={
            "email": "invitee@example.com",
            "invited_by": str(inviter),
            "role": "admin",
        },
        headers=_headers(tenant_id),
    )
    token = r.json()["token"]

    r2 = await client.post(
        "/api/v1/invitations/accept", json={"token": token, "user_id": str(invitee)}
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["user_id"] == str(invitee)
    assert data["role"] == "admin"

    members = await client.get(
        f"/api/v1/organizations/{org_id}/members", headers=_headers(tenant_id)
    )
    assert members.json()["total"] == 1


@pytest.mark.asyncio
async def test_accept_invitation_replay_prevented(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    inviter = uuid.uuid4()
    invitee = uuid.uuid4()

    r = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "invitee@example.com", "invited_by": str(inviter)},
        headers=_headers(tenant_id),
    )
    token = r.json()["token"]

    r2 = await client.post(
        "/api/v1/invitations/accept", json={"token": token, "user_id": str(invitee)}
    )
    assert r2.status_code == 200

    r3 = await client.post(
        "/api/v1/invitations/accept",
        json={"token": token, "user_id": str(uuid.uuid4())},
    )
    assert r3.status_code == 409


@pytest.mark.asyncio
async def test_accept_invitation_unknown_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/invitations/accept",
        json={"token": "not-a-real-token", "user_id": str(uuid.uuid4())},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_invitations(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "a@example.com", "invited_by": str(uuid.uuid4())},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/organizations/{org_id}/invitations", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1
    # token/token_hash must never appear in the list response
    assert "token" not in r.json()["items"][0]


@pytest.mark.asyncio
async def test_revoke_invitation(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    invite = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "a@example.com", "invited_by": str(uuid.uuid4())},
        headers=_headers(tenant_id),
    )
    invitation_id = invite.json()["id"]
    token = invite.json()["token"]

    r = await client.post(
        f"/api/v1/organizations/{org_id}/invitations/{invitation_id}/revoke",
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"

    accept = await client.post(
        "/api/v1/invitations/accept",
        json={"token": token, "user_id": str(uuid.uuid4())},
    )
    assert accept.status_code == 409


@pytest.mark.asyncio
async def test_revoke_invitation_not_found(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.post(
        f"/api/v1/organizations/{org_id}/invitations/{uuid.uuid4()}/revoke",
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404
