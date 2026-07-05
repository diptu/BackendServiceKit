"""Preferences: locale/timezone/extra, defaults, independence from other resources."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import FakeUserProfileClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_get_preferences_no_row_yet_returns_defaults(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    r = await client.get(f"/api/v1/profiles/{user_id}/preferences")
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "en"
    assert body["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_update_preferences(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id)

    r = await client.patch(
        f"/api/v1/profiles/{user_id}/preferences",
        json={"locale": "bn", "timezone": "Asia/Dhaka", "extra": {"newsletter": False}},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "bn"
    assert body["timezone"] == "Asia/Dhaka"
    assert body["extra"] == {"newsletter": False}


@pytest.mark.asyncio
async def test_updating_preferences_does_not_create_profile_row(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id)

    await client.patch(
        f"/api/v1/profiles/{user_id}/preferences",
        json={"locale": "fr"},
        headers=_headers(tenant_id),
    )
    profile = await client.get(f"/api/v1/profiles/{user_id}")
    assert profile.json()["created_at"] is None
