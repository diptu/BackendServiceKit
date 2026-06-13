"""
UserSocialLink schemas.

Represents social media links associated with a user profile.

Used for:
- user profile enrichment
- public identity representation
- optional social graph features
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

# =========================================================
# BASE
# =========================================================

class UserSocialLinkBase(BaseModel):
    """
    Shared fields for social links.
    """

    platform: str = Field(..., min_length=1, max_length=50)

    url: HttpUrl

    is_public: bool = True


# =========================================================
# CREATE
# =========================================================

class UserSocialLinkCreate(UserSocialLinkBase):
    """
    Create a social link for a user.
    """

    user_id: uuid.UUID


# =========================================================
# UPDATE
# =========================================================

class UserSocialLinkUpdate(BaseModel):
    """
    Update social link.

    All fields optional (PATCH semantics).
    """

    platform: str | None = Field(default=None, max_length=50)

    url: HttpUrl | None = None

    is_public: bool | None = None


# =========================================================
# INTERNAL DB MODEL
# =========================================================

class UserSocialLinkInDB(BaseModel):
    """
    Internal DB representation.
    """

    id: uuid.UUID

    user_id: uuid.UUID

    platform: str
    url: str

    is_public: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class UserSocialLinkOut(UserSocialLinkBase):
    """
    Public API response schema.

    Safe for profile exposure.
    """

    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)