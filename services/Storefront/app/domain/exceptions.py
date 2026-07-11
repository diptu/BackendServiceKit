"""Domain exceptions for the Storefront service."""

from __future__ import annotations

from uuid import UUID


class NotFoundError(Exception):
    """Base for 404-mapped errors."""


class ConflictError(Exception):
    """Base for 409-mapped errors."""


class ValidationError(Exception):
    """Base for 422-mapped domain validation errors."""


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: UUID) -> None:
        super().__init__(f"Product {product_id} not found.")
        self.product_id = product_id


class VariantNotFoundError(NotFoundError):
    def __init__(self, variant_id: UUID) -> None:
        super().__init__(f"Variant {variant_id} not found.")
        self.variant_id = variant_id


class CategoryNotFoundError(NotFoundError):
    def __init__(self, category_id: UUID) -> None:
        super().__init__(f"Category {category_id} not found.")
        self.category_id = category_id


class CartNotFoundError(NotFoundError):
    def __init__(self, cart_id: UUID) -> None:
        super().__init__(f"Cart {cart_id} not found.")
        self.cart_id = cart_id


class OrderNotFoundError(NotFoundError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Order {order_id} not found.")
        self.order_id = order_id


class SlugConflictError(ConflictError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"Slug '{slug}' is already in use.")
        self.slug = slug


class SkuConflictError(ConflictError):
    def __init__(self, sku: str) -> None:
        super().__init__(f"SKU '{sku}' is already in use.")
        self.sku = sku


class OutOfStockError(ValidationError):
    def __init__(self, sku: str, requested: int, available: int) -> None:
        super().__init__(
            f"Not enough stock for SKU '{sku}': requested {requested}, "
            f"available {available}."
        )
        self.sku = sku
        self.requested = requested
        self.available = available


class EmptyCartError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Cannot check out an empty cart.")


class InvalidOrderStatusTransitionError(ConflictError):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Invalid order status transition: {from_status} -> {to_status}."
        )
        self.from_status = from_status
        self.to_status = to_status
