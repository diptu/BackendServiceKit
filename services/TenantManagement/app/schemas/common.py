"""Shared Pydantic schemas used across multiple endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.constants import DEFAULT_PAGINATION_LIMIT, MAX_PAGINATION_LIMIT


class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(
        default=DEFAULT_PAGINATION_LIMIT,
        ge=1,
        le=MAX_PAGINATION_LIMIT,
    )


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
