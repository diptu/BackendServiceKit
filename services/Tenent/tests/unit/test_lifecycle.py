"""TenantLifecycle endpoint tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _tenant_payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": f"lc-{uuid.uuid4().hex[:8]}",
        "display_name": "Lifecycle Test",
        "region": "us-west-2",
        "owner_id": str(uuid.uuid4()),
    }
    base.update(kwargs)
    return base


async def _create_tenant(client: AsyncClient) -> str:
    r = await client.post("/api/v1/tenants", json=_tenant_payload())
    assert r.status_code == 201
    return str(r.json()["id"])


@pytest.mark.asyncio
async def test_provision_creates_lifecycle_record(client: AsyncClient) -> None:
    tenant_id = await _create_tenant(client)
    r = await client.put(
        f"/api/v1/lifecycle/{tenant_id}/provision", json={"reason": "initial setup"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == tenant_id
    assert data["current_status"] == "provisioning"


@pytest.mark.asyncio
async def test_get_lifecycle_state(client: AsyncClient) -> None:
    tenant_id = await _create_tenant(client)
    await client.put(f"/api/v1/lifecycle/{tenant_id}/provision", json={})

    r = await client.get(f"/api/v1/lifecycle/{tenant_id}")
    assert r.status_code == 200
    assert r.json()["current_status"] == "provisioning"


@pytest.mark.asyncio
async def test_lifecycle_not_found(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/lifecycle/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_full_lifecycle_flow(client: AsyncClient) -> None:
    """provision → pend → activate → suspend → reactivate."""
    tenant_id = await _create_tenant(client)

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/provision", json={})
    assert r.json()["current_status"] == "provisioning"

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/pend", json={})
    assert r.json()["current_status"] == "pending"

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/activate", json={})
    assert r.json()["current_status"] == "active"

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/suspend", json={})
    assert r.json()["current_status"] == "suspended"

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/reactivate", json={})
    assert r.json()["current_status"] == "active"


@pytest.mark.asyncio
async def test_lock_unlock(client: AsyncClient) -> None:
    tenant_id = await _create_tenant(client)
    for endpoint in ("provision", "pend", "activate"):
        await client.put(f"/api/v1/lifecycle/{tenant_id}/{endpoint}", json={})

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/lock", json={"reason": "security hold"})
    assert r.json()["current_status"] == "locked"

    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/unlock", json={})
    assert r.json()["current_status"] == "active"


@pytest.mark.asyncio
async def test_lifecycle_history(client: AsyncClient) -> None:
    tenant_id = await _create_tenant(client)
    await client.put(f"/api/v1/lifecycle/{tenant_id}/provision", json={})
    await client.put(f"/api/v1/lifecycle/{tenant_id}/pend", json={})

    r = await client.get(f"/api/v1/lifecycle/{tenant_id}/history")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert len(data["events"]) >= 2


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition(client: AsyncClient) -> None:
    tenant_id = await _create_tenant(client)
    await client.put(f"/api/v1/lifecycle/{tenant_id}/provision", json={})
    # provisioning → activate is invalid (must pend first)
    r = await client.put(f"/api/v1/lifecycle/{tenant_id}/activate", json={})
    assert r.status_code == 409
