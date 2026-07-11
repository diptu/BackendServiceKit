"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant

__all__ = [
    "Cart",
    "CartItem",
    "Category",
    "Order",
    "OrderItem",
    "Product",
    "ProductVariant",
]
