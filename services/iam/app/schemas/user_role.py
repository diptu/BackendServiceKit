"""
UserRole schemas for RBAC IAM system.

Represents assignment of roles to users, including:
- role grants
- optional expiration
- audit metadata
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# BASE
# =========================================================

class UserRoleBase(BaseModel):
    """
    Shared fields for user-role assignment.
    """

    user_id: uuid.UUID
    role_id: uuid.UUID


# =========================================================
# CREATE (role assignment)
# =========================================================

class UserRoleCreate(UserRoleBase):
    """
    Assign a role to a user.
    """

    assigned_by: uuid.UUID | None = None

    expires_at: datetime | None = None


# =========================================================
# UPDATE (rare but useful for expiry extension)
# =========================================================

class UserRoleUpdate(BaseModel):
    """
    Update a user-role assignment.

    Typically used for:
    - extending expiration
    - revoking assignment (soft-expire)
    """

    expires_at: datetime | None = None


# =========================================================
# INTERNAL DB MODEL
# =========================================================

class UserRoleInDB(BaseModel):
    """
    Internal DB representation of UserRole.
    """

    id: uuid.UUID

    user_id: uuid.UUID
    role_id: uuid.UUID

    assigned_by: uuid.UUID | None
    assigned_at: datetime

    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class UserRoleOut(UserRoleBase):
    """
    Public API representation of role assignment.
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

class UserRoleShortOut(BaseModel):
    """
    Minimal representation for authorization checks.

    Used in:
    - JWT enrichment
    - /authorize endpoint
    - policy engine evaluation
    """

    user_id: uuid.UUID
    role_id: uuid.UUID

    expires_at: datetime | None

    model_config = ConfigDict(from_attributes=True)