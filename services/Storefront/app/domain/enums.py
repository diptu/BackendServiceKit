"""Domain enumerations for the Storefront (e-commerce) service."""

from __future__ import annotations

from enum import StrEnum


class ProductStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class CartStatus(StrEnum):
    OPEN = "open"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


# Allowed order status transitions. Terminal states map to an empty set.
ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.PAID, OrderStatus.CANCELLED}),
    OrderStatus.PAID: frozenset({OrderStatus.FULFILLED, OrderStatus.CANCELLED}),
    OrderStatus.FULFILLED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}
