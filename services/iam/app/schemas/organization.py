"""
Organization schemas for multi-tenancy (IAM service).

Defines API contracts for:
- Organization creation / update / responses
- Membership management (add / update role / list)
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.role import RoleShortOut

# =========================================================
# BASE
# =========================================================


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=500)


# =========================================================
# CREATE / UPDATE
# =========================================================


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization. The creator becomes its owner."""


class OrganizationUpdate(BaseModel):
    """Slug is immutable once created — it may be referenced externally."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


# =========================================================
# RESPONSES
# =========================================================


class UserOutMinimal(BaseModel):
    id: uuid.UUID
    email: str

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberOut(BaseModel):
    id: uuid.UUID
    user: UserOutMinimal
    role: RoleShortOut
    is_active: bool
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationOut(OrganizationBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OrganizationDetailOut(OrganizationOut):
    members: list[OrganizationMemberOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OrganizationPageResponse(BaseModel):
    items: list[OrganizationOut]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def build(
        cls,
        items: list[OrganizationOut],
        total: int,
        page: int,
        page_size: int,
    ) -> OrganizationPageResponse:
        pages = max(1, math.ceil(total / page_size)) if total else 1
        return cls(
            items=items, total=total, page=page, page_size=page_size, pages=pages
        )


# =========================================================
# MEMBERSHIP MUTATIONS
# =========================================================


class MemberAddRequest(BaseModel):
    """
    Add an existing platform user to an organization.

    Exactly one of `role_id` / `role_slug` must be given; omitting both
    defaults to the seeded `org_member` role.
    """

    user_id: uuid.UUID
    role_id: uuid.UUID | None = None
    role_slug: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _at_most_one_role_selector(self) -> MemberAddRequest:
        if self.role_id is not None and self.role_slug is not None:
            raise ValueError("Provide either role_id or role_slug, not both.")
        return self


class MemberRoleUpdateRequest(BaseModel):
    """Change the role an existing member holds within the organization."""

    role_id: uuid.UUID | None = None
    role_slug: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _exactly_one_role_selector(self) -> MemberRoleUpdateRequest:
        if (self.role_id is None) == (self.role_slug is None):
            raise ValueError("Provide exactly one of role_id or role_slug.")
        return self
