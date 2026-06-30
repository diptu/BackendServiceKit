"""Isolation endpoints tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validate_same_tenant(client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/isolation/validate",
        json={"caller_tenant_id": tenant_id, "target_tenant_id": tenant_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] is True
    assert data["decision"] == "allow"


@pytest.mark.asyncio
async def test_validate_cross_tenant_no_policy(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/isolation/validate",
        json={
            "caller_tenant_id": str(uuid.uuid4()),
            "target_tenant_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] is False
    assert data["decision"] == "deny"


@pytest.mark.asyncio
async def test_policy_create_and_list(client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/isolation/policies?tenant_id={tenant_id}",
        json={"name": "strict-policy", "policy_type": "strict"},
    )
    assert r.status_code == 201
    policy = r.json()
    assert policy["name"] == "strict-policy"
    assert policy["policy_type"] == "strict"
    assert policy["tenant_id"] == tenant_id

    r2 = await client.get(f"/api/v1/isolation/policies?tenant_id={tenant_id}")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1


@pytest.mark.asyncio
async def test_policy_get_update(client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/isolation/policies?tenant_id={tenant_id}",
        json={"name": "original-name"},
    )
    policy_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/isolation/policies/{policy_id}")
    assert r2.status_code == 200

    r3 = await client.patch(
        f"/api/v1/isolation/policies/{policy_id}",
        json={"name": "updated-name"},
    )
    assert r3.status_code == 200
    assert r3.json()["name"] == "updated-name"


@pytest.mark.asyncio
async def test_resource_claim_and_release(client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    resource_id = f"doc-{uuid.uuid4().hex[:8]}"

    r = await client.post(
        "/api/v1/isolation/claims",
        json={
            "tenant_id": tenant_id,
            "resource_id": resource_id,
            "resource_type": "document",
            "source_service": "test",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["tenant_id"] == tenant_id
    assert data["resource_id"] == resource_id

    r2 = await client.get(f"/api/v1/isolation/claims?tenant_id={tenant_id}")
    assert r2.status_code == 200

    r3 = await client.request(
        "DELETE",
        "/api/v1/isolation/claims",
        json={
            "tenant_id": tenant_id,
            "resource_id": resource_id,
            "resource_type": "document",
        },
    )
    assert r3.status_code == 204


@pytest.mark.asyncio
async def test_resource_claim_conflict(client: AsyncClient) -> None:
    tid1 = str(uuid.uuid4())
    tid2 = str(uuid.uuid4())
    resource_id = f"doc-{uuid.uuid4().hex[:8]}"

    r1 = await client.post(
        "/api/v1/isolation/claims",
        json={
            "tenant_id": tid1,
            "resource_id": resource_id,
            "resource_type": "document",
            "source_service": "test",
        },
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/isolation/claims",
        json={
            "tenant_id": tid2,
            "resource_id": resource_id,
            "resource_type": "document",
            "source_service": "test",
        },
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_validate_query_valid(client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/isolation/validate-query",
        json={"caller_tenant_id": tenant_id, "filters": {"tenant_id": tenant_id}},
    )
    assert r.status_code == 200
    assert r.json()["valid"] is True


@pytest.mark.asyncio
async def test_validate_query_missing_tenant_id(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/isolation/validate-query",
        json={"caller_tenant_id": str(uuid.uuid4()), "filters": {"name": "foo"}},
    )
    assert r.status_code == 422
