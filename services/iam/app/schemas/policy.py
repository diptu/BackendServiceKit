"""
Policy schemas for IAM system.

Defines API contracts for:
- policy creation
- policy updates
- policy evaluation payloads
- policy responses

Supports RBAC + ABAC style authorization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# BASE
# =========================================================

class PolicyBase(BaseModel):
    """
    Shared policy fields.
    """

    name: str = Field(..., min_length=1, max_length=255)

    description: str | None = Field(default=None)

    effect: str = Field(..., pattern="^(allow|deny)$")

    resource: str = Field(..., min_length=1, max_length=100)

    action: str = Field(..., min_length=1, max_length=100)

    conditions: dict[str, Any] | None = Field(default=None)


# =========================================================
# CREATE
# =========================================================

class PolicyCreate(PolicyBase):
    """
    Schema for creating a policy.
    """

    created_by: uuid.UUID | None = None


# =========================================================
# UPDATE
# =========================================================

class PolicyUpdate(BaseModel):
    """
    Schema for updating a policy.

    All fields optional (PATCH semantics).
    """

    name: str | None = Field(default=None, max_length=255)

    description: str | None = None

    effect: str | None = Field(default=None, pattern="^(allow|deny)$")

    resource: str | None = Field(default=None, max_length=100)

    action: str | None = Field(default=None, max_length=100)

    conditions: dict[str, Any] | None = None

    is_active: bool | None = None


# =========================================================
# INTERNAL (DB LAYER)
# =========================================================

class PolicyInDB(BaseModel):
    """
    Internal DB representation of Policy.
    """

    id: uuid.UUID

    name: str
    description: str | None

    effect: str
    resource: str
    action: str

    conditions: dict[str, Any] | None

    version: int
    is_active: bool

    created_by: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class PolicyOut(PolicyBase):
    """
    Public API response schema.

    Safe for:
    - admin dashboards
    - policy inspection APIs
    """

    id: uuid.UUID

    version: int
    is_active: bool

    created_by: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# POLICY EVALUATION INPUT (VERY IMPORTANT)
# =========================================================

class PolicyContext(BaseModel):
    """
    Context passed to policy engine for evaluation.

    Used in /authorize requests.
    """

    user_id: uuid.UUID

    resource: str

    action: str

    attributes: dict[str, Any] = Field(default_factory=dict)

    # Example attributes:
    # {
    #   "ip": "10.0.0.1",
    #   "device": "mobile",
    #   "tenant_id": "..."
    # }


# =========================================================
# POLICY DECISION OUTPUT
# =========================================================

class PolicyDecision(BaseModel):
    """
    Output of policy engine evaluation.
    """

    allowed: bool

    reason: str | None = None

    matched_policy_ids: list[uuid.UUID] = Field(default_factory=list)

    effect: str | None = None  # allow / deny

    model_config = ConfigDict(from_attributes=True)