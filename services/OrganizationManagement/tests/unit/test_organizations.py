"""Organization CRUD, settings, stats, sub-resource, and tenant-scoping tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.api.v1.dependencies import get_tenent_client
from app.domain.exceptions import TenantNotFoundError, TenantServiceUnavailableError
from app.main import app


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": "Acme Corporation",
        "slug": f"acme-{uuid.uuid4().hex[:8]}",
    }
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_organization(client: AsyncClient) -> None:
    r = await client.post("/api/v1/organizations", json=_payload(), headers=_headers())
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_organization_requires_tenant_header(client: AsyncClient) -> None:
    r = await client.post("/api/v1/organizations", json=_payload())
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_organization_duplicate_slug_same_tenant(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    slug = f"dup-{uuid.uuid4().hex[:8]}"
    r1 = await client.post(
        "/api/v1/organizations", json=_payload(slug=slug), headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/organizations", json=_payload(slug=slug), headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_organization_same_slug_different_tenant_allowed(
    client: AsyncClient,
) -> None:
    slug = f"shared-{uuid.uuid4().hex[:8]}"
    r1 = await client.post(
        "/api/v1/organizations", json=_payload(slug=slug), headers=_headers()
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/organizations", json=_payload(slug=slug), headers=_headers()
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_create_organization_tenant_not_found(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()

    class _NotFoundClient:
        async def assert_tenant_exists(self, tid: uuid.UUID) -> None:
            raise TenantNotFoundError(tid)

    app.dependency_overrides[get_tenent_client] = lambda: _NotFoundClient()
    try:
        r = await client.post(
            "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
        )
    finally:
        app.dependency_overrides.pop(get_tenent_client, None)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_organization_tenant_service_unavailable(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()

    class _UnavailableClient:
        async def assert_tenant_exists(self, tid: uuid.UUID) -> None:
            raise TenantServiceUnavailableError(tid)

    app.dependency_overrides[get_tenent_client] = lambda: _UnavailableClient()
    try:
        r = await client.post(
            "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
        )
    finally:
        app.dependency_overrides.pop(get_tenent_client, None)
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_get_organization(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == org_id


@pytest.mark.asyncio
async def test_get_organization_not_found(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/organizations/{uuid.uuid4()}", headers=_headers())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_organization_wrong_tenant_is_not_found(
    client: AsyncClient,
) -> None:
    """Cross-tenant isolation: an org created under tenant A must be
    invisible to a caller presenting tenant B's header, even with the
    correct organization_id."""
    r = await client.post("/api/v1/organizations", json=_payload(), headers=_headers())
    org_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/organizations/{org_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_organizations(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    r = await client.get("/api/v1/organizations", headers=_headers(tenant_id))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_update_organization(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/organizations/{org_id}",
        json={"name": "Updated Name"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_organization(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.delete(
        f"/api/v1/organizations/{org_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 204

    r3 = await client.get(
        f"/api/v1/organizations/{org_id}", headers=_headers(tenant_id)
    )
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_get_and_update_settings(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}/settings", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json()["timezone"] == "UTC"

    r3 = await client.patch(
        f"/api/v1/organizations/{org_id}/settings",
        json={"timezone": "America/New_York", "feature_flags": {"beta": True}},
        headers=_headers(tenant_id),
    )
    assert r3.status_code == 200
    assert r3.json()["timezone"] == "America/New_York"
    assert r3.json()["feature_flags"] == {"beta": True}


@pytest.mark.asyncio
async def test_get_stats(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}/stats", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["member_count"] == 0
    assert data["workspace_count"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("sub_resource", ["workspaces", "groups"])
async def test_sub_resource_enumeration_is_empty(
    client: AsyncClient, sub_resource: str
) -> None:
    """Workspaces/Groups have no owning storage yet — still the honest,
    hardcoded empty stub (see TODO.md). Members/Teams graduated to real
    storage and are covered by test_memberships.py/test_teams.py instead."""
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}/{sub_resource}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    assert r2.json() == {"items": [], "total": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("sub_resource", ["members", "teams"])
async def test_new_sub_resources_have_real_paginated_envelope(
    client: AsyncClient, sub_resource: str
) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/organizations", json=_payload(), headers=_headers(tenant_id)
    )
    org_id = r.json()["id"]

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}/{sub_resource}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["has_more"] is False
    assert data["next_cursor"] is None
