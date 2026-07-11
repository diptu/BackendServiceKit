"""Catalog (category + product + variant) API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

TENANT = "11111111-1111-1111-1111-111111111111"
H = {"X-Tenant-ID": TENANT}


@pytest.mark.asyncio
async def test_create_category_and_product_with_variants(client: AsyncClient) -> None:
    cat = await client.post(
        "/api/v1/categories",
        headers=H,
        json={"name": "Dresses", "slug": "dresses"},
    )
    assert cat.status_code == 201, cat.text
    category_id = cat.json()["id"]

    prod = await client.post(
        "/api/v1/products",
        headers=H,
        json={
            "name": "Willow Wrap Dress",
            "slug": "willow-wrap-dress",
            "description": "Breezy linen wrap dress",
            "price_cents": 8900,
            "currency": "USD",
            "status": "active",
            "category_id": category_id,
            "variants": [
                {
                    "sku": "WWD-S-SAGE",
                    "size": "S",
                    "color": "Sage",
                    "stock_quantity": 4,
                },
                {
                    "sku": "WWD-M-SAGE",
                    "size": "M",
                    "color": "Sage",
                    "stock_quantity": 6,
                },
            ],
        },
    )
    assert prod.status_code == 201, prod.text
    body = prod.json()
    assert body["status"] == "active"
    assert len(body["variants"]) == 2
    assert {v["sku"] for v in body["variants"]} == {"WWD-S-SAGE", "WWD-M-SAGE"}


@pytest.mark.asyncio
async def test_slug_conflict_returns_409(client: AsyncClient) -> None:
    payload = {"name": "Tee", "slug": "classic-tee", "price_cents": 2500}
    first = await client.post("/api/v1/products", headers=H, json=payload)
    assert first.status_code == 201
    dup = await client.post("/api/v1/products", headers=H, json=payload)
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_list_and_get_product(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/products",
        headers=H,
        json={
            "name": "Scarf",
            "slug": "wool-scarf",
            "price_cents": 3200,
            "status": "active",
        },
    )
    pid = created.json()["id"]

    listed = await client.get(
        "/api/v1/products", headers=H, params={"status": "active"}
    )
    assert listed.status_code == 200
    assert any(p["id"] == pid for p in listed.json()["items"])

    one = await client.get(f"/api/v1/products/{pid}", headers=H)
    assert one.status_code == 200
    assert one.json()["slug"] == "wool-scarf"


@pytest.mark.asyncio
async def test_missing_tenant_header_is_400(client: AsyncClient) -> None:
    res = await client.get("/api/v1/products")
    assert res.status_code == 400
