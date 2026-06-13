"""
Permission schemas for RBAC IAM system.

Defines API contracts for:
- Permission creation
- Permission updates
- Permission responses
- Internal DB representation
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# BASE
# =========================================================

class PermissionBase(BaseModel):
    """
    Shared permission fields.
    """

    name: str = Field(..., min_length=1, max_length=255)

    resource: str = Field(..., min_length=1, max_length=100)

    action: str = Field(..., min_length=1, max_length=100)

    description: str | None = Field(default=None, max_length=500)


# =========================================================
# CREATE
# =========================================================

class PermissionCreate(PermissionBase):
    """
    Schema for creating a permission.
    """
    pass


# =========================================================
# UPDATE
# =========================================================

class PermissionUpdate(BaseModel):
    """
    Schema for updating a permission.

    All fields optional for PATCH semantics.
    """

    name: str | None = Field(default=None, max_length=255)

    resource: str | None = Field(default=None, max_length=100)

    action: str | None = Field(default=None, max_length=100)

    description: str | None = Field(default=None, max_length=500)


# =========================================================
# INTERNAL (DB LAYER)
# =========================================================

class PermissionInDB(BaseModel):
    """
    Internal DB representation of Permission.
    """

    id: uuid.UUID

    name: str
    resource: str
    action: str
    description: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class PermissionOut(PermissionBase):
    """
    Public API response schema.

    Safe to expose in:
    - role details
    - admin dashboards
    - IAM inspection APIs
    """

    id: uuid.UUID

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# LIGHTWEIGHT DTO (for RBAC + policy engine)
# =========================================================

class PermissionShortOut(BaseModel):
    """
    Minimal permission representation for:
    - JWT claims
    - authorization checks
    - policy evaluation engine
    """

    id: uuid.UUID
    name: str  # e.g. "users:create"
    resource: str
    action: str

    model_config = ConfigDict(from_attributes=True)