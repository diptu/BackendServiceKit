"""
UserProfile schemas.

Represents non-IAM identity data separated from core authentication system.

Used for:
- user profile management
- identity enrichment (ABAC context)
- public profile rendering
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# BASE
# =========================================================


class UserProfileBase(BaseModel):
    """
    Shared profile fields.
    """

    full_name: str | None = Field(default=None, max_length=150)

    avatar_url: str | None = Field(default=None, max_length=2048)

    bio: str | None = Field(default=None, max_length=500)


# =========================================================
# CREATE
# =========================================================


class UserProfileCreate(UserProfileBase):
    """
    Create user profile.
    """

    user_id: uuid.UUID


# =========================================================
# UPDATE
# =========================================================


class UserProfileUpdate(BaseModel):
    """
    Update profile fields.

    All fields optional (PATCH semantics).
    """

    full_name: str | None = Field(default=None, max_length=150)

    avatar_url: str | None = Field(default=None, max_length=2048)

    bio: str | None = Field(default=None, max_length=500)


# =========================================================
# INTERNAL DB MODEL
# =========================================================


class UserProfileInDB(BaseModel):
    """
    Internal DB representation of UserProfile.
    """

    user_id: uuid.UUID

    full_name: str | None
    avatar_url: str | None
    bio: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================


class UserProfileOut(UserProfileBase):
    """
    Public API representation of user profile.

    Safe for:
    - /users/me
    - public profile pages
    - IAM context enrichment (non-sensitive)
    """

    user_id: uuid.UUID

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
