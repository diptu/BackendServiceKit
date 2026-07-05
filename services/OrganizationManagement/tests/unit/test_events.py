"""Organization audit-trail (domain events) endpoint."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


@pytest.mark.asyncio
async def test_create_organization_records_event(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme", "slug": f"acme-{uuid.uuid4().hex[:8]}"},
        headers=_headers(tenant_id),
    )
    org_id = r.json()["id"]

    events = await client.get(
        f"/api/v1/organizations/{org_id}/events", headers=_headers(tenant_id)
    )
    assert events.status_code == 200
    data = events.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "OrganizationCreated"


@pytest.mark.asyncio
async def test_events_accumulate_across_mutations(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme", "slug": f"acme-{uuid.uuid4().hex[:8]}"},
        headers=_headers(tenant_id),
    )
    org_id = r.json()["id"]

    await client.patch(
        f"/api/v1/organizations/{org_id}",
        json={"name": "Acme Renamed"},
        headers=_headers(tenant_id),
    )
    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(uuid.uuid4())},
        headers=_headers(tenant_id),
    )

    events = await client.get(
        f"/api/v1/organizations/{org_id}/events", headers=_headers(tenant_id)
    )
    event_types = {e["event_type"] for e in events.json()["items"]}
    assert event_types == {"OrganizationCreated", "OrganizationUpdated", "MemberAdded"}


@pytest.mark.asyncio
async def test_events_scoped_to_organization(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org1 = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Org1", "slug": f"org1-{uuid.uuid4().hex[:8]}"},
            headers=_headers(tenant_id),
        )
    ).json()["id"]
    await client.post(
        "/api/v1/organizations",
        json={"name": "Org2", "slug": f"org2-{uuid.uuid4().hex[:8]}"},
        headers=_headers(tenant_id),
    )

    events = await client.get(
        f"/api/v1/organizations/{org1}/events", headers=_headers(tenant_id)
    )
    assert events.json()["total"] == 1
