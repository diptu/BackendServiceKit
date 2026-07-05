"""Read-only Users endpoints — UserProjection is seeded directly (no write API).

See app/models/user_projection.py's docstring and services/IAM/TODO.md:
writes only ever come from the (deferred) user.created/updated/deleted
event consumer, never this service's own HTTP API.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_projection import UserProjection


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


async def _seed_user(db_session: AsyncSession, tenant_id: uuid.UUID) -> UserProjection:
    user = UserProjection(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        display_name="Test User",
        status="active",
        synced_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user = await _seed_user(db_session, tenant_id)

    r = await client.get(f"/api/v1/users/{user.id}", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["id"] == str(user.id)


@pytest.mark.asyncio
async def test_get_user_wrong_tenant_is_not_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _seed_user(db_session, uuid.uuid4())

    r = await client.get(f"/api/v1/users/{user.id}", headers=_headers())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=_headers())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, db_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _seed_user(db_session, tenant_id)

    r = await client.get("/api/v1/users", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1
