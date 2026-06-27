"""Pydantic schemas for the Tenant Management Service."""

from app.schemas.base import AppBaseModel
from app.schemas.common import ErrorResponse, PaginationParams

__all__ = ["AppBaseModel", "ErrorResponse", "PaginationParams"]
