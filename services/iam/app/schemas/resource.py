"""
Resource schemas for IAM system.

Resources represent protected system entities that can be
secured through permissions and policies.

Examples:
    users
    roles
    payments
    documents
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

    schema: dict[str, Any] | None = None

    is_public: bool = False


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

    schema: dict[str, Any] | None = None

    is_public: bool | None = None

    is_active: bool | None = None


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

    schema: dict[str, Any] | None

    is_public: bool
    is_active: bool

    created_by: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# LIGHTWEIGHT DTO
# =========================================================

class ResourceShortOut(BaseModel):
    """
    Lightweight resource representation.

    Useful for:
    - permission responses
    - policy responses
    - authorization engine
    """

    id: uuid.UUID

    name: str

    type: str

    model_config = ConfigDict(from_attributes=True)