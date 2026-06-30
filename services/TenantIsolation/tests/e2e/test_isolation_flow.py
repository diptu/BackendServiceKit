"""E2E tests — full isolation flow via HTTP client + real SQLite."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.dependencies import get_db
from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_full_flow_claim_then_validate(client: AsyncClient) -> None:
    tenant_id = str(uuid4())
    resource_id = str(uuid4())

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
    assert r.json()["tenant_id"] == tenant_id

    r = await client.post(
        "/api/v1/isolation/validate",
        json={
            "caller_tenant_id": tenant_id,
            "resource_ids": [resource_id],
            "resource_type": "document",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "allow"
    assert r.json()["violations"] == []


async def test_cross_tenant_validate_denied(client: AsyncClient) -> None:
    owner_id = str(uuid4())
    caller_id = str(uuid4())
    resource_id = str(uuid4())

    r = await client.post(
        "/api/v1/isolation/claims",
        json={
            "tenant_id": owner_id,
            "resource_id": resource_id,
            "resource_type": "workspace",
            "source_service": "test",
        },
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/v1/isolation/validate",
        json={
            "caller_tenant_id": caller_id,
            "resource_ids": [resource_id],
            "resource_type": "workspace",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "deny"
    assert resource_id in r.json()["violations"]


async def test_claim_then_release_then_validate_denied(client: AsyncClient) -> None:
    tid = str(uuid4())
    rid = str(uuid4())

    r = await client.post(
        "/api/v1/isolation/claims",
        json={"tenant_id": tid, "resource_id": rid, "resource_type": "role", "source_service": "svc"},
    )
    assert r.status_code == 201

    r = await client.request(
        "DELETE",
        "/api/v1/isolation/claims",
        json={"tenant_id": tid, "resource_id": rid, "resource_type": "role"},
    )
    assert r.status_code == 204

    r = await client.post(
        "/api/v1/isolation/validate",
        json={"caller_tenant_id": tid, "resource_ids": [rid], "resource_type": "role"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "deny"
    assert rid in r.json()["violations"]


async def test_check_access_logs_decision(client: AsyncClient) -> None:
    caller = str(uuid4())
    target = str(uuid4())

    r = await client.post(
        "/api/v1/isolation/check-access",
        json={
            "caller_tenant_id": caller,
            "target_tenant_id": target,
            "resource_id": "res-audit",
            "resource_type": "document",
            "action": "read",
        },
    )
    assert r.status_code == 200

    r = await client.get(f"/api/v1/isolation/decisions?tenant_id={caller}")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    decisions = r.json()["items"]
    assert any(d["resource_id"] == "res-audit" for d in decisions)


async def test_validate_query_enforcement(client: AsyncClient) -> None:
    tid = str(uuid4())

    r = await client.post(
        "/api/v1/isolation/validate-query",
        json={"caller_tenant_id": tid, "query_filter": {"tenant_id": tid, "status": "active"}},
    )
    assert r.status_code == 200
    assert r.json()["is_valid"] is True

    r = await client.post(
        "/api/v1/isolation/validate-query",
        json={"caller_tenant_id": tid, "query_filter": {"status": "active"}},
    )
    assert r.status_code == 422


async def test_create_and_list_policies(client: AsyncClient, mocker: object) -> None:
    """Policies can be listed (creation is via direct DB in integration tests)."""
    tid = str(uuid4())
    r = await client.get(f"/api/v1/isolation/policies?tenant_id={tid}")
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0
