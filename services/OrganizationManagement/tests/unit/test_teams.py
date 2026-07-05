"""Team/Department CRUD, hierarchy, team membership, tenant scoping."""

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


def _team_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"team-{uuid.uuid4().hex[:8]}"}
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_team(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(),
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["team_type"] == "team"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_department(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(team_type="department"),
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    assert r.json()["team_type"] == "department"


@pytest.mark.asyncio
async def test_create_team_duplicate_name(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    name = f"dup-{uuid.uuid4().hex[:8]}"

    r1 = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(name=name),
        headers=_headers(tenant_id),
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(name=name),
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_team_with_invalid_parent(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(parent_team_id=str(uuid.uuid4())),
        headers=_headers(tenant_id),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_team_with_valid_parent_hierarchy(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    parent = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(name="engineering", team_type="department"),
        headers=_headers(tenant_id),
    )
    parent_id = parent.json()["id"]

    child = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(name="backend-team", parent_team_id=parent_id),
        headers=_headers(tenant_id),
    )
    assert child.status_code == 201
    assert child.json()["parent_team_id"] == parent_id


@pytest.mark.asyncio
async def test_get_team_not_found(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)

    r = await client.get(
        f"/api/v1/organizations/{org_id}/teams/{uuid.uuid4()}",
        headers=_headers(tenant_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_team(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    team = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(),
        headers=_headers(tenant_id),
    )
    team_id = team.json()["id"]

    r = await client.patch(
        f"/api/v1/organizations/{org_id}/teams/{team_id}",
        json={"name": "renamed-team"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["name"] == "renamed-team"


@pytest.mark.asyncio
async def test_delete_team(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    team = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(),
        headers=_headers(tenant_id),
    )
    team_id = team.json()["id"]

    r = await client.delete(
        f"/api/v1/organizations/{org_id}/teams/{team_id}", headers=_headers(tenant_id)
    )
    assert r.status_code == 204

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}/teams/{team_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_teams(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(),
        headers=_headers(tenant_id),
    )

    r = await client.get(
        f"/api/v1/organizations/{org_id}/teams", headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_team_membership(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    org_id = await _create_org(client, tenant_id)
    team = await client.post(
        f"/api/v1/organizations/{org_id}/teams",
        json=_team_payload(),
        headers=_headers(tenant_id),
    )
    team_id = team.json()["id"]
    user_id = uuid.uuid4()

    r = await client.post(
        f"/api/v1/organizations/{org_id}/teams/{team_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204

    r2 = await client.get(
        f"/api/v1/organizations/{org_id}/teams/{team_id}/members",
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["items"] == [str(user_id)]

    r3 = await client.post(
        f"/api/v1/organizations/{org_id}/teams/{team_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    assert r3.status_code == 409

    r4 = await client.delete(
        f"/api/v1/organizations/{org_id}/teams/{team_id}/members/{user_id}",
        headers=_headers(tenant_id),
    )
    assert r4.status_code == 204

    r5 = await client.delete(
        f"/api/v1/organizations/{org_id}/teams/{team_id}/members/{user_id}",
        headers=_headers(tenant_id),
    )
    assert r5.status_code == 404
