"""
Resource schemas for IAM system.

Resources represent protected system entities that can be
secured through permissions and policies.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# BASE
# =========================================================


class ResourceBase(BaseModel):
    """
    Shared resource fields.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    type: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    description: str | None = None

    # Fix: Renamed from 'schema' to avoid namespace collision with BaseModel.schema
    resource_schema: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        serialization_alias="schema",
        validation_alias="schema",
    )

    is_public: bool = False

    # This ensures you can access or populate the model using both `resource_schema` and `schema`
    model_config = ConfigDict(populate_by_name=True)


# =========================================================
# CREATE
# =========================================================


class ResourceCreate(ResourceBase):
    """
    Create a resource.
    """

    created_by: uuid.UUID | None = None


# =========================================================
# UPDATE
# =========================================================


class ResourceUpdate(BaseModel):
    """
    Update a resource.

    Supports PATCH semantics.
    """

    name: str | None = Field(
        default=None,
        max_length=100,
    )

    type: str | None = Field(
        default=None,
        max_length=50,
    )

    description: str | None = None

    # Fix: Renamed here as well
    resource_schema: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        serialization_alias="schema",
        validation_alias="schema",
    )

    is_public: bool | None = None

    is_active: bool | None = None

    model_config = ConfigDict(populate_by_name=True)


# =========================================================
# INTERNAL DB
# =========================================================


class ResourceInDB(BaseModel):
    """
    Internal database representation.
    """

    id: uuid.UUID

    name: str
    type: str

    description: str | None

    # Fix: Renamed here as well
    resource_schema: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        serialization_alias="schema",
        validation_alias="schema",
    )

    is_public: bool
    is_active: bool

    created_by: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================


class ResourceOut(ResourceBase):
    """
    Resource API response.
    """

    id: uuid.UUID

    is_active: bool

    created_by: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =========================================================
# LIGHTWEIGHT DTO
# =========================================================


class ResourceShortOut(BaseModel):
    """
    Lightweight resource representation.
    """

    id: uuid.UUID

    name: str

    type: str

    model_config = ConfigDict(from_attributes=True)
