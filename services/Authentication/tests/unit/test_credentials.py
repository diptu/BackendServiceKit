"""Credential creation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_set_credential(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/credentials",
        json={
            "user_id": str(user_id),
            "email": "ada@example.com",
            "password": "correct-horse-battery-staple",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_set_credential_duplicate_email_conflicts(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    body = {
        "user_id": str(uuid.uuid4()),
        "email": "dup@example.com",
        "password": "correct-horse-battery-staple",
    }
    r1 = await client.post(
        "/api/v1/auth/credentials", json=body, headers=_headers(tenant_id)
    )
    assert r1.status_code == 204

    body2 = {**body, "user_id": str(uuid.uuid4())}
    r2 = await client.post(
        "/api/v1/auth/credentials", json=body2, headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_same_email_allowed_across_different_tenants(
    client: AsyncClient,
) -> None:
    email = "cross-tenant@example.com"
    r1 = await client.post(
        "/api/v1/auth/credentials",
        json={
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password": "correct-horse-battery-staple",
        },
        headers=_headers(uuid.uuid4()),
    )
    assert r1.status_code == 204

    r2 = await client.post(
        "/api/v1/auth/credentials",
        json={
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password": "correct-horse-battery-staple",
        },
        headers=_headers(uuid.uuid4()),
    )
    assert r2.status_code == 204
