"""AbacPolicy CRUD, tenant scoping, and the /authorization/evaluate decision engine."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": f"policy-{uuid.uuid4().hex[:8]}",
        "effect": "allow",
        "resource_type": "document",
        "action": "read",
    }
    base.update(kwargs)
    return base


async def _set_attribute(
    client: AsyncClient,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    key: str,
    value: object,
) -> None:
    value_type = (
        "number"
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else "boolean"
        if isinstance(value, bool)
        else "string"
    )
    r = await client.post(
        f"/api/v1/user-attributes/{user_id}",
        json={"key": key, "value": value, "value_type": value_type},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201


async def _grant_rbac_permission(
    client: AsyncClient, tenant_id: uuid.UUID, user_id: uuid.UUID, permission_name: str
) -> None:
    headers = _headers(tenant_id)
    role_r = await client.post(
        "/api/v1/roles",
        json={"name": f"role-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    role_id = role_r.json()["id"]

    perm_r = await client.post(
        "/api/v1/permissions", json={"name": permission_name}, headers=headers
    )
    permission_id = perm_r.json()["id"]

    add_r = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=headers,
    )
    assert add_r.status_code == 204

    assign_r = await client.post(
        f"/api/v1/user-roles/{user_id}",
        json={"role_id": role_id},
        headers=headers,
    )
    assert assign_r.status_code == 204


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_policy(client: AsyncClient) -> None:
    r = await client.post("/api/v1/policies", json=_payload(), headers=_headers())
    assert r.status_code == 201
    body = r.json()
    assert body["effect"] == "allow"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_create_policy_duplicate_name_same_tenant(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    name = f"dup-{uuid.uuid4().hex[:8]}"
    r1 = await client.post(
        "/api/v1/policies", json=_payload(name=name), headers=_headers(tenant_id)
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/policies", json=_payload(name=name), headers=_headers(tenant_id)
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_policy_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    r = await client.post("/api/v1/policies", json=_payload(), headers=_headers())
    policy_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/policies/{policy_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_policies(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post("/api/v1/policies", json=_payload(), headers=_headers(tenant_id))
    r = await client.get("/api/v1/policies", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_policy(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/policies", json=_payload(), headers=_headers(tenant_id)
    )
    policy_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/policies/{policy_id}",
        json={"priority": 5, "is_active": False},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["priority"] == 5
    assert body["is_active"] is False


@pytest.mark.asyncio
async def test_delete_policy(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/policies", json=_payload(), headers=_headers(tenant_id)
    )
    policy_id = r.json()["id"]

    r2 = await client.delete(
        f"/api/v1/policies/{policy_id}", headers=_headers(tenant_id)
    )
    assert r2.status_code == 204

    r3 = await client.get(f"/api/v1/policies/{policy_id}", headers=_headers(tenant_id))
    assert r3.status_code == 404


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_allow_policy_matching_attributes_permits(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _set_attribute(client, tenant_id, user_id, "department", "engineering")
    await _set_attribute(client, tenant_id, user_id, "clearance_level", 3)

    await client.post(
        "/api/v1/policies",
        json=_payload(
            resource_type="report",
            action="view",
            conditions={
                "all": [
                    {"attribute": "department", "op": "eq", "value": "engineering"},
                    {"attribute": "clearance_level", "op": "gte", "value": 3},
                ]
            },
        ),
        headers=_headers(tenant_id),
    )

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={"user_id": str(user_id), "resource_type": "report", "action": "view"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is True
    assert body["matched_policy_id"] is not None


@pytest.mark.asyncio
async def test_evaluate_deny_policy_blocks(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _set_attribute(client, tenant_id, user_id, "region", "eu")

    await client.post(
        "/api/v1/policies",
        json=_payload(
            name=f"deny-{uuid.uuid4().hex[:8]}",
            effect="deny",
            resource_type="export",
            action="download",
            conditions={"attribute": "region", "op": "eq", "value": "eu"},
        ),
        headers=_headers(tenant_id),
    )

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={"user_id": str(user_id), "resource_type": "export", "action": "download"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["matched_policy_id"] is not None


@pytest.mark.asyncio
async def test_evaluate_no_policy_no_rbac_denies_by_default(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={
            "user_id": str(user_id),
            "resource_type": "widget",
            "action": "delete",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["reason"] == "no_matching_policy_and_no_rbac_permission"
    assert body["matched_policy_id"] is None


@pytest.mark.asyncio
async def test_evaluate_falls_back_to_rbac_when_no_policy_matches(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _grant_rbac_permission(client, tenant_id, user_id, "widget:create")

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={
            "user_id": str(user_id),
            "resource_type": "widget",
            "action": "create",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is True
    assert body["reason"] == "rbac_permission_grant"
    assert body["matched_policy_id"] is None


@pytest.mark.asyncio
async def test_evaluate_explicit_deny_overrides_rbac_grant(
    client: AsyncClient,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _grant_rbac_permission(client, tenant_id, user_id, "widget:archive")

    await client.post(
        "/api/v1/policies",
        json=_payload(
            name=f"deny-{uuid.uuid4().hex[:8]}",
            effect="deny",
            resource_type="widget",
            action="archive",
            conditions=None,
        ),
        headers=_headers(tenant_id),
    )

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={
            "user_id": str(user_id),
            "resource_type": "widget",
            "action": "archive",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["matched_policy_id"] is not None


@pytest.mark.asyncio
async def test_evaluate_operators_in_and_exists(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _set_attribute(client, tenant_id, user_id, "team", "platform")

    await client.post(
        "/api/v1/policies",
        json=_payload(
            resource_type="dashboard",
            action="view",
            conditions={
                "all": [
                    {"attribute": "team", "op": "in", "value": ["platform", "sre"]},
                    {"attribute": "team", "op": "exists"},
                ]
            },
        ),
        headers=_headers(tenant_id),
    )

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={"user_id": str(user_id), "resource_type": "dashboard", "action": "view"},
        headers=_headers(tenant_id),
    )
    assert r.json()["allowed"] is True


@pytest.mark.asyncio
async def test_evaluate_is_tenant_isolated(client: AsyncClient) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    user_id = uuid.uuid4()

    # A blanket allow policy in tenant A must not leak into tenant B's
    # evaluation for the same resource_type/action/user_id.
    await client.post(
        "/api/v1/policies",
        json=_payload(resource_type="invoice", action="approve", conditions=None),
        headers=_headers(tenant_a),
    )

    r = await client.post(
        "/api/v1/authorization/evaluate",
        json={"user_id": str(user_id), "resource_type": "invoice", "action": "approve"},
        headers=_headers(tenant_b),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["matched_policy_id"] is None
