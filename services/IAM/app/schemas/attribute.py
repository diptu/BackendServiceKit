"""Pydantic schemas for user Attribute endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import AttributeValueType
from app.schemas.base import AppBaseModel

_AttributeValue = str | float | bool | list[object]


class CreateAttributeRequest(AppBaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: _AttributeValue
    value_type: AttributeValueType


class UpdateAttributeRequest(AppBaseModel):
    value: _AttributeValue | None = None
    value_type: AttributeValueType | None = None


class AttributeResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    key: str
    value: _AttributeValue
    value_type: AttributeValueType
    created_at: datetime
    updated_at: datetime


class AttributeListResponse(AppBaseModel):
    items: list[AttributeResponse]
    total: int
