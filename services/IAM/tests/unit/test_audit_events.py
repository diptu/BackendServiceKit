"""Audit trail: role assignment, role<->permission linkage, group membership,
tenant membership, and entitlement grant/revoke all record an AuditEvent."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _role_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"role-{uuid.uuid4().hex[:8]}"}
    base.update(kwargs)
    return base


def _permission_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"perm-{uuid.uuid4().hex[:8]}:read"}
    base.update(kwargs)
    return base


def _group_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"name": f"group-{uuid.uuid4().hex[:8]}"}
    base.update(kwargs)
    return base


async def _list_events(
    client: AsyncClient, tenant_id: uuid.UUID, **params: str
) -> list[dict[str, object]]:
    r = await client.get(
        "/api/v1/audit-events", params=params, headers=_headers(tenant_id)
    )
    assert r.status_code == 200
    items: list[dict[str, object]] = r.json()["items"]
    return items


@pytest.mark.asyncio
async def test_role_assignment_records_event(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]

    r = await client.post(
        f"/api/v1/user-roles/{user_id}",
        json={"role_id": role_id, "performed_by": str(actor_id)},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204

    events = await _list_events(client, tenant_id, subject_user_id=str(user_id))
    assert len(events) == 1
    assert events[0]["event_type"] == "role.assigned"
    assert events[0]["resource_type"] == "role"
    assert events[0]["resource_id"] == role_id
    assert events[0]["subject_user_id"] == str(user_id)
    assert events[0]["actor_id"] == str(actor_id)


@pytest.mark.asyncio
async def test_role_unassignment_records_event(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/user-roles/{user_id}",
        json={"role_id": role_id},
        headers=_headers(tenant_id),
    )

    r = await client.delete(
        f"/api/v1/user-roles/{user_id}/{role_id}", headers=_headers(tenant_id)
    )
    assert r.status_code == 204

    events = await _list_events(client, tenant_id, subject_user_id=str(user_id))
    event_types = {e["event_type"] for e in events}
    assert "role.assigned" in event_types
    assert "role.unassigned" in event_types


@pytest.mark.asyncio
async def test_actor_id_defaults_to_none_when_not_supplied(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]

    await client.post(
        f"/api/v1/user-roles/{user_id}",
        json={"role_id": role_id},
        headers=_headers(tenant_id),
    )

    events = await _list_events(client, tenant_id, subject_user_id=str(user_id))
    assert events[0]["actor_id"] is None


@pytest.mark.asyncio
async def test_role_permission_linkage_records_events(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]
    permission_id = (
        await client.post(
            "/api/v1/permissions",
            json=_permission_payload(),
            headers=_headers(tenant_id),
        )
    ).json()["id"]

    await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_id": permission_id},
        headers=_headers(tenant_id),
    )
    await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{permission_id}",
        headers=_headers(tenant_id),
    )

    events = await _list_events(client, tenant_id, resource_type="role")
    event_types = {e["event_type"] for e in events}
    assert "role.permission_added" in event_types
    assert "role.permission_removed" in event_types
    added = next(e for e in events if e["event_type"] == "role.permission_added")
    assert added["details"] == {"permission_id": permission_id}


@pytest.mark.asyncio
async def test_group_membership_records_events(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    group_id = (
        await client.post(
            "/api/v1/groups", json=_group_payload(), headers=_headers(tenant_id)
        )
    ).json()["id"]

    await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": str(user_id)},
        headers=_headers(tenant_id),
    )
    await client.delete(
        f"/api/v1/groups/{group_id}/members/{user_id}", headers=_headers(tenant_id)
    )

    events = await _list_events(client, tenant_id, subject_user_id=str(user_id))
    event_types = {e["event_type"] for e in events}
    assert "group.member_added" in event_types
    assert "group.member_removed" in event_types


@pytest.mark.asyncio
async def test_tenant_membership_records_events(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await client.post(
        f"/api/v1/tenant-memberships/{tenant_id}/members",
        json={"user_id": str(user_id)},
    )
    await client.delete(f"/api/v1/tenant-memberships/{tenant_id}/members/{user_id}")

    events = await _list_events(client, tenant_id, subject_user_id=str(user_id))
    event_types = {e["event_type"] for e in events}
    assert "tenant_membership.added" in event_types
    assert "tenant_membership.removed" in event_types


@pytest.mark.asyncio
async def test_entitlement_grant_and_revoke_record_events(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    r = await client.post(
        "/api/v1/entitlements",
        json={"user_id": str(user_id), "key": "seats", "value": 5},
        headers=_headers(tenant_id),
    )
    entitlement_id = r.json()["id"]

    await client.delete(
        f"/api/v1/entitlements/{entitlement_id}", headers=_headers(tenant_id)
    )

    events = await _list_events(client, tenant_id, subject_user_id=str(user_id))
    event_types = {e["event_type"] for e in events}
    assert "entitlement.granted" in event_types
    assert "entitlement.revoked" in event_types


@pytest.mark.asyncio
async def test_audit_events_scoped_by_tenant(client: AsyncClient) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    user_id = uuid.uuid4()
    role_id = (
        await client.post(
            "/api/v1/roles", json=_role_payload(), headers=_headers(tenant_a)
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/user-roles/{user_id}",
        json={"role_id": role_id},
        headers=_headers(tenant_a),
    )

    events_b = await _list_events(client, tenant_b)
    assert events_b == []
