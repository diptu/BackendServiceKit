"""Tenant-scoped data access for products and their variants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    # ----- products --------------------------------------------------------
    async def create(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        return product

    async def get_by_id(self, product_id: UUID, *, tenant_id: UUID) -> Product | None:
        stmt = select(Product).where(
            Product.id == product_id, Product.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, slug: str, *, tenant_id: UUID) -> bool:
        stmt = select(Product.id).where(
            Product.slug == slug, Product.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def list_products(
        self,
        *,
        tenant_id: UUID,
        status: str | None = None,
        category_id: UUID | None = None,
    ) -> list[Product]:
        stmt = select(Product).where(Product.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(Product.status == status)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        stmt = stmt.order_by(Product.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete(self, product: Product) -> None:
        await self._session.delete(product)
        await self._session.flush()

    # ----- variants --------------------------------------------------------
    async def add_variant(self, variant: ProductVariant) -> ProductVariant:
        self._session.add(variant)
        await self._session.flush()
        return variant

    async def get_variant(
        self, variant_id: UUID, *, tenant_id: UUID
    ) -> ProductVariant | None:
        stmt = select(ProductVariant).where(
            ProductVariant.id == variant_id, ProductVariant.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_variants(
        self, product_id: UUID, *, tenant_id: UUID
    ) -> list[ProductVariant]:
        stmt = (
            select(ProductVariant)
            .where(
                ProductVariant.product_id == product_id,
                ProductVariant.tenant_id == tenant_id,
            )
            .order_by(ProductVariant.sku)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def sku_exists(self, sku: str, *, tenant_id: UUID) -> bool:
        stmt = select(ProductVariant.id).where(
            ProductVariant.sku == sku, ProductVariant.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def delete_variant(self, variant: ProductVariant) -> None:
        await self._session.delete(variant)
        await self._session.flush()
