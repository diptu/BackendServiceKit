"""Contact info: phone/secondary_email/address."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import FakeUserProfileClient


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


@pytest.mark.asyncio
async def test_get_contacts_no_row_yet_returns_defaults(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    r = await client.get(f"/api/v1/profiles/{user_id}/contacts")
    assert r.status_code == 200
    assert r.json()["phone"] is None


@pytest.mark.asyncio
async def test_update_contacts(
    client: AsyncClient, fake_client: FakeUserProfileClient
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_client.seed(user_id)

    r = await client.patch(
        f"/api/v1/profiles/{user_id}/contacts",
        json={
            "phone": "+8801700000000",
            "secondary_email": "backup@example.com",
            "address": {"city": "Dhaka", "country": "BD"},
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["phone"] == "+8801700000000"
    assert body["secondary_email"] == "backup@example.com"
    assert body["address"] == {"city": "Dhaka", "country": "BD"}


@pytest.mark.asyncio
async def test_update_contacts_unknown_user_404s(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    r = await client.patch(
        f"/api/v1/profiles/{user_id}/contacts",
        json={"phone": "+1234567890"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404
