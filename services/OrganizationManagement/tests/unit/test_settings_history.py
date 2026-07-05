"""Organization settings version-history endpoint."""

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
async def test_settings_history_empty_before_any_update(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.get(
        f"/api/v1/organizations/{org_id}/settings/history", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_settings_update_creates_history_entry(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    await client.patch(
        f"/api/v1/organizations/{org_id}/settings",
        json={"timezone": "America/New_York"},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/organizations/{org_id}/settings/history", headers=_headers(tenant_id)
    )
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["version"] == 1
    assert data["items"][0]["snapshot"]["timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_settings_history_versions_increment(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    await client.patch(
        f"/api/v1/organizations/{org_id}/settings",
        json={"timezone": "America/New_York"},
        headers=_headers(tenant_id),
    )
    await client.patch(
        f"/api/v1/organizations/{org_id}/settings",
        json={"locale": "fr-FR"},
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/organizations/{org_id}/settings/history", headers=_headers(tenant_id)
    )
    data = r.json()
    assert data["total"] == 2
    versions = sorted(item["version"] for item in data["items"])
    assert versions == [1, 2]
