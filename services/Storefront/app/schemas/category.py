"""Category request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class CreateCategoryRequest(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str | None = None


class CategoryResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(AppBaseModel):
    items: list[CategoryResponse]
    total: int
