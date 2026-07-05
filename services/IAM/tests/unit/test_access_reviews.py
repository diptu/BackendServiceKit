"""Access Review create/list/detail/record-decision, tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _headers(tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id or uuid.uuid4())}


def _payload(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "subject_user_id": str(uuid.uuid4()),
        "resource_type": "role",
        "resource_id": str(uuid.uuid4()),
    }
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_access_review(client: AsyncClient) -> None:
    r = await client.post("/api/v1/access-reviews", json=_payload(), headers=_headers())
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_get_access_review_wrong_tenant_is_not_found(client: AsyncClient) -> None:
    r = await client.post("/api/v1/access-reviews", json=_payload(), headers=_headers())
    review_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/access-reviews/{review_id}", headers=_headers())
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_access_reviews(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await client.post(
        "/api/v1/access-reviews", json=_payload(), headers=_headers(tenant_id)
    )
    r = await client.get("/api/v1/access-reviews", headers=_headers(tenant_id))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_record_access_review_decision(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/access-reviews", json=_payload(), headers=_headers(tenant_id)
    )
    review_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/access-reviews/{review_id}",
        json={"status": "approved", "decision_notes": "looks fine"},
        headers=_headers(tenant_id),
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["status"] == "approved"
    assert data["decision_notes"] == "looks fine"
    assert data["reviewed_at"] is not None
