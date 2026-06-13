"""
RolePermission schemas for RBAC IAM system.

Represents assignment of permissions to roles, including:
- permission grants
- optional expiration
- audit metadata
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# =========================================================
# BASE
# =========================================================

class RolePermissionBase(BaseModel):
    """
    Shared fields for role-permission assignment.
    """

    role_id: uuid.UUID
    permission_id: uuid.UUID


# =========================================================
# CREATE
# =========================================================

class RolePermissionCreate(RolePermissionBase):
    """
    Assign a permission to a role.
    """

    assigned_by: uuid.UUID | None = None

    expires_at: datetime | None = None


# =========================================================
# UPDATE
# =========================================================

class RolePermissionUpdate(BaseModel):
    """
    Update role-permission assignment.

    Used for:
    - extending expiration
    - revoking permission
    """

    expires_at: datetime | None = None


# =========================================================
# INTERNAL DB MODEL
# =========================================================

class RolePermissionInDB(BaseModel):
    """
    Internal DB representation of RolePermission.
    """

    id: uuid.UUID

    role_id: uuid.UUID
    permission_id: uuid.UUID

    assigned_by: uuid.UUID | None
    assigned_at: datetime

    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class RolePermissionOut(RolePermissionBase):
    """
    Public API representation of role-permission mapping.
    """

    id: uuid.UUID

    assigned_by: uuid.UUID | None
    assigned_at: datetime

    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# LIGHTWEIGHT DTO (AUTH / POLICY ENGINE)
# =========================================================

class RolePermissionShortOut(BaseModel):
    """
    Minimal representation used for:
    - authorization checks
    - policy engine evaluation
    - cached RBAC graphs
    """

    role_id: uuid.UUID
    permission_id: uuid.UUID

    expires_at: datetime | None

    model_config = ConfigDict(from_attributes=True)