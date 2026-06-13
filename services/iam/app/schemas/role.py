"""
Role schemas for RBAC (IAM service).

Defines API contracts for:
- Role creation
- Role updates
- Role responses
- Internal DB representation
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# BASE
# =========================================================

class RoleBase(BaseModel):
    """
    Shared role fields.
    """
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


# =========================================================
# CREATE
# =========================================================

class RoleCreate(RoleBase):
    """
    Schema for creating a role.
    """
    is_system: bool = Field(default=False)


# =========================================================
# UPDATE
# =========================================================

class RoleUpdate(BaseModel):
    """
    Schema for updating a role.

    All fields optional to support PATCH semantics.
    """

    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    is_system: bool | None = None


# =========================================================
# INTERNAL (DB LAYER)
# =========================================================

class RoleInDB(BaseModel):
    """
    Internal DB representation of Role.
    """

    id: uuid.UUID

    name: str
    slug: str
    description: str | None

    is_system: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# MINIMAL RELATED DTOs (for RBAC graph exposure)
# =========================================================

class PermissionOut(BaseModel):
    """
    Lightweight permission representation.

    (kept minimal to avoid over-fetching in role APIs)
    """
    id: uuid.UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class UserOutMinimal(BaseModel):
    """
    Minimal user representation inside role responses.
    """
    id: uuid.UUID
    email: str

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class RoleOut(RoleBase):
    """
    Public role response schema.

    SAFE: includes only necessary RBAC exposure.
    """

    id: uuid.UUID

    is_system: bool

    created_at: datetime
    updated_at: datetime

    users: list[UserOutMinimal] = Field(default_factory=list)
    permissions: list[PermissionOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# LIGHTWEIGHT RESPONSE (for dropdowns / auth context)
# =========================================================

class RoleShortOut(BaseModel):
    """
    Minimal role representation for auth contexts.
    Useful in JWT claims or `/me` endpoints.
    """

    id: uuid.UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)