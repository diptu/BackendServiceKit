"""Shared Pydantic schemas used across multiple endpoints."""

from __future__ import annotations

from pydantic import Field

from app.core.constants import DEFAULT_PAGINATION_LIMIT, MAX_PAGINATION_LIMIT
from app.schemas.base import AppBaseModel


class PaginationParams(AppBaseModel):
    next_cursor: str | None = None
    limit: int = Field(
        default=DEFAULT_PAGINATION_LIMIT,
        ge=1,
        le=MAX_PAGINATION_LIMIT,
    )


class ErrorResponse(AppBaseModel):
    detail: str
    error_code: str | None = None
