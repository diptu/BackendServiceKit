from __future__ import annotations

import math
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserOut
from app.schemas.userProfile.user_profile import UserProfileOut


class UserListParams(BaseModel):
    q: str | None = Field(default=None, description="Search by email or full_name")
    role: str | None = Field(default=None, description="Filter by role slug")
    is_active: bool | None = None
    is_verified: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class UserPageResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def build(
        cls, items: list[UserOut], total: int, page: int, page_size: int
    ) -> UserPageResponse:
        pages = max(1, math.ceil(total / page_size)) if total else 1
        return cls(
            items=items, total=total, page=page, page_size=page_size, pages=pages
        )


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_verified: bool | None = None


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    avatar_url: str | None = Field(default=None, max_length=2048)
    bio: str | None = Field(default=None, max_length=500)


class UserWithProfileOut(UserOut):
    profile_detail: UserProfileOut | None = Field(default=None, alias="profile_full")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Re-export for convenience in endpoints
__all__ = [
    "AdminUserUpdate",
    "ProfileUpdateRequest",
    "UserListParams",
    "UserPageResponse",
    "UserProfileOut",
    "UserWithProfileOut",
    "uuid",
]
