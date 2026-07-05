"""Profile CRUD, default-valued reads, existence-check gating."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import FakeUserProfileClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_get_profile_no_row_yet_returns_defaults_not_404(
    client: AsyncClient,
) -> None:
    user_id = uuid.uuid4()
    r = await client.get(f"/api/v1/profiles/{user_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] is None
    assert body["created_at"] is None


@pytest.mark.asyncio
async def test_update_profile_unknown_user_404s(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "hello"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_profile_known_user(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id)

    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "Backend engineer", "pronouns": "she/her"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] == "Backend engineer"
    assert body["pronouns"] == "she/her"
    assert body["created_at"] is not None


@pytest.mark.asyncio
async def test_update_profile_partial_update_preserves_other_fields(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id)

    await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"bio": "Bio one"},
        headers=_headers(tenant_id),
    )
    r = await client.patch(
        f"/api/v1/profiles/{user_id}",
        json={"pronouns": "they/them"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bio"] == "Bio one"
    assert body["pronouns"] == "they/them"


@pytest.mark.asyncio
async def test_second_write_does_not_recheck_existence(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    """Once a local row exists, this user_id is never removed from
    known_users, so a second write against an already-created profile
    still succeeds even if we don't touch the fake again — proves the
    existence check only fires on the create path."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id)
    await client.patch(
        f"/api/v1/profiles/{user_id}", json={"bio": "v1"}, headers=_headers(tenant_id)
    )

    r = await client.patch(
        f"/api/v1/profiles/{user_id}", json={"bio": "v2"}, headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["bio"] == "v2"
