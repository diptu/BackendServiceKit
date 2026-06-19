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

    NOTE: `slug` is intentionally unconstrained in format here — `RoleOut`
    (the API *response* schema) extends this base, and system-seeded roles
    (e.g. "org_owner", "super_admin", see app.core.rbac) use underscores.
    The hyphen-only format constraint for *new* roles lives on
    `RoleCreate`/`RoleUpdate` instead, where it only governs input.
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

    organization_id: None creates a global/platform role (platform-admin
    only); set it to scope a custom role to one organization.
    permission_slugs: existing Permission slugs to attach at creation time.
    """

    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    organization_id: uuid.UUID | None = Field(default=None)
    is_system: bool = Field(default=False)
    permission_slugs: list[str] = Field(default_factory=list)


# =========================================================
# UPDATE
# =========================================================


class RoleUpdate(BaseModel):
    """
    Schema for updating a role.

    All fields optional to support PATCH semantics.
    """

    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=500)

    is_system: bool | None = None


class RolePermissionsAssignRequest(BaseModel):
    """Body for adding one or more existing permissions to a role."""

    permission_slugs: list[str] = Field(..., min_length=1)


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

    organization_id: uuid.UUID | None = None
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
