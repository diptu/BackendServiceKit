"""Cart + checkout flow tests — the core commerce path."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

TENANT = "22222222-2222-2222-2222-222222222222"
H = {"X-Tenant-ID": TENANT}


async def _make_product(client: AsyncClient, *, stock: int, price: int) -> str:
    res = await client.post(
        "/api/v1/products",
        headers=H,
        json={
            "name": "Everyday Tee",
            "slug": "everyday-tee",
            "price_cents": price,
            "status": "active",
            "variants": [
                {
                    "sku": "TEE-M-BLK",
                    "size": "M",
                    "color": "Black",
                    "stock_quantity": stock,
                }
            ],
        },
    )
    assert res.status_code == 201, res.text
    return str(res.json()["variants"][0]["id"])


@pytest.mark.asyncio
async def test_add_to_cart_and_checkout(client: AsyncClient) -> None:
    variant_id = await _make_product(client, stock=5, price=2000)

    cart = await client.post(
        "/api/v1/carts", headers=H, json={"customer_ref": "shopper-1"}
    )
    assert cart.status_code == 201, cart.text
    cart_id = cart.json()["id"]

    added = await client.post(
        f"/api/v1/carts/{cart_id}/items",
        headers=H,
        json={"variant_id": variant_id, "quantity": 2},
    )
    assert added.status_code == 201, added.text
    assert added.json()["subtotal_cents"] == 4000

    order = await client.post(
        "/api/v1/orders/checkout",
        headers=H,
        json={"cart_id": cart_id, "email": "shopper@example.com"},
    )
    assert order.status_code == 201, order.text
    ob = order.json()
    assert ob["status"] == "pending"
    assert ob["total_cents"] == 4000
    assert ob["items"][0]["quantity"] == 2
    assert ob["items"][0]["sku"] == "TEE-M-BLK"

    # Stock was decremented 5 -> 3
    prod = await client.get("/api/v1/products", headers=H)
    variant = prod.json()["items"][0]["variants"][0]
    assert variant["stock_quantity"] == 3


@pytest.mark.asyncio
async def test_out_of_stock_is_rejected(client: AsyncClient) -> None:
    variant_id = await _make_product(client, stock=1, price=1000)
    cart = await client.post("/api/v1/carts", headers=H, json={})
    cart_id = cart.json()["id"]
    res = await client.post(
        f"/api/v1/carts/{cart_id}/items",
        headers=H,
        json={"variant_id": variant_id, "quantity": 5},
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_checkout_empty_cart_is_422(client: AsyncClient) -> None:
    cart = await client.post("/api/v1/carts", headers=H, json={})
    cart_id = cart.json()["id"]
    res = await client.post(
        "/api/v1/orders/checkout", headers=H, json={"cart_id": cart_id}
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_order_status_transition(client: AsyncClient) -> None:
    variant_id = await _make_product(client, stock=3, price=1500)
    cart = await client.post("/api/v1/carts", headers=H, json={})
    cart_id = cart.json()["id"]
    await client.post(
        f"/api/v1/carts/{cart_id}/items",
        headers=H,
        json={"variant_id": variant_id, "quantity": 1},
    )
    order = await client.post(
        "/api/v1/orders/checkout", headers=H, json={"cart_id": cart_id}
    )
    order_id = order.json()["id"]

    paid = await client.post(
        f"/api/v1/orders/{order_id}/status", headers=H, json={"status": "paid"}
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    # pending -> fulfilled is not allowed once paid? paid -> fulfilled IS allowed.
    fulfilled = await client.post(
        f"/api/v1/orders/{order_id}/status", headers=H, json={"status": "fulfilled"}
    )
    assert fulfilled.status_code == 200

    # fulfilled is terminal -> cancelling should 409
    cancel = await client.post(
        f"/api/v1/orders/{order_id}/status", headers=H, json={"status": "cancelled"}
    )
    assert cancel.status_code == 409
