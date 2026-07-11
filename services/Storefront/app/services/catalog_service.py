"""Catalog business logic: categories, products, and variants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import (
    CategoryNotFoundError,
    ProductNotFoundError,
    SkuConflictError,
    SlugConflictError,
    VariantNotFoundError,
)
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductRepository
from app.schemas.category import CategoryResponse, CreateCategoryRequest
from app.schemas.product import (
    CreateProductRequest,
    CreateVariantRequest,
    ProductResponse,
    UpdateProductRequest,
    VariantResponse,
)


def _variant_response(v: ProductVariant) -> VariantResponse:
    return VariantResponse.model_validate(v)


def _product_response(
    product: Product, variants: list[ProductVariant]
) -> ProductResponse:
    resp = ProductResponse.model_validate(product)
    resp.variants = [_variant_response(v) for v in variants]
    return resp


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._categories = CategoryRepository(session)
        self._products = ProductRepository(session)

    # ----- categories ------------------------------------------------------
    async def create_category(
        self, tenant_id: UUID, req: CreateCategoryRequest
    ) -> CategoryResponse:
        if await self._categories.slug_exists(req.slug, tenant_id=tenant_id):
            raise SlugConflictError(req.slug)
        category = Category(
            tenant_id=tenant_id,
            name=req.name,
            slug=req.slug,
            description=req.description,
        )
        await self._categories.create(category)
        return CategoryResponse.model_validate(category)

    async def list_categories(self, tenant_id: UUID) -> list[CategoryResponse]:
        rows = await self._categories.list_all(tenant_id=tenant_id)
        return [CategoryResponse.model_validate(c) for c in rows]

    async def delete_category(self, tenant_id: UUID, category_id: UUID) -> None:
        category = await self._categories.get_by_id(category_id, tenant_id=tenant_id)
        if category is None:
            raise CategoryNotFoundError(category_id)
        await self._categories.delete(category)

    # ----- products --------------------------------------------------------
    async def create_product(
        self, tenant_id: UUID, req: CreateProductRequest
    ) -> ProductResponse:
        if await self._products.slug_exists(req.slug, tenant_id=tenant_id):
            raise SlugConflictError(req.slug)
        if req.category_id is not None:
            category = await self._categories.get_by_id(
                req.category_id, tenant_id=tenant_id
            )
            if category is None:
                raise CategoryNotFoundError(req.category_id)

        product = Product(
            tenant_id=tenant_id,
            category_id=req.category_id,
            name=req.name,
            slug=req.slug,
            description=req.description,
            image_url=req.image_url,
            price_cents=req.price_cents,
            currency=req.currency,
            status=req.status.value,
        )
        await self._products.create(product)

        variants: list[ProductVariant] = []
        for v in req.variants:
            variants.append(await self._create_variant(tenant_id, product.id, v))
        return _product_response(product, variants)

    async def get_product(self, tenant_id: UUID, product_id: UUID) -> ProductResponse:
        product = await self._require_product(tenant_id, product_id)
        variants = await self._products.list_variants(product.id, tenant_id=tenant_id)
        return _product_response(product, variants)

    async def list_products(
        self,
        tenant_id: UUID,
        *,
        status: str | None = None,
        category_id: UUID | None = None,
    ) -> list[ProductResponse]:
        products = await self._products.list_products(
            tenant_id=tenant_id, status=status, category_id=category_id
        )
        out: list[ProductResponse] = []
        for p in products:
            variants = await self._products.list_variants(p.id, tenant_id=tenant_id)
            out.append(_product_response(p, variants))
        return out

    async def update_product(
        self, tenant_id: UUID, product_id: UUID, req: UpdateProductRequest
    ) -> ProductResponse:
        product = await self._require_product(tenant_id, product_id)
        data = req.model_dump(exclude_unset=True)
        if "status" in data and data["status"] is not None:
            data["status"] = req.status.value if req.status is not None else None
        if "category_id" in data and data["category_id"] is not None:
            category = await self._categories.get_by_id(
                data["category_id"], tenant_id=tenant_id
            )
            if category is None:
                raise CategoryNotFoundError(data["category_id"])
        for key, value in data.items():
            setattr(product, key, value)
        await self._session.flush()
        await self._session.refresh(product)
        variants = await self._products.list_variants(product.id, tenant_id=tenant_id)
        return _product_response(product, variants)

    async def delete_product(self, tenant_id: UUID, product_id: UUID) -> None:
        product = await self._require_product(tenant_id, product_id)
        await self._products.delete(product)

    # ----- variants --------------------------------------------------------
    async def add_variant(
        self, tenant_id: UUID, product_id: UUID, req: CreateVariantRequest
    ) -> VariantResponse:
        await self._require_product(tenant_id, product_id)
        variant = await self._create_variant(tenant_id, product_id, req)
        return _variant_response(variant)

    async def delete_variant(self, tenant_id: UUID, variant_id: UUID) -> None:
        variant = await self._products.get_variant(variant_id, tenant_id=tenant_id)
        if variant is None:
            raise VariantNotFoundError(variant_id)
        await self._products.delete_variant(variant)

    # ----- helpers ---------------------------------------------------------
    async def _require_product(self, tenant_id: UUID, product_id: UUID) -> Product:
        product = await self._products.get_by_id(product_id, tenant_id=tenant_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    async def _create_variant(
        self, tenant_id: UUID, product_id: UUID, req: CreateVariantRequest
    ) -> ProductVariant:
        if await self._products.sku_exists(req.sku, tenant_id=tenant_id):
            raise SkuConflictError(req.sku)
        variant = ProductVariant(
            tenant_id=tenant_id,
            product_id=product_id,
            sku=req.sku,
            size=req.size,
            color=req.color,
            price_cents=req.price_cents,
            stock_quantity=req.stock_quantity,
        )
        return await self._products.add_variant(variant)
