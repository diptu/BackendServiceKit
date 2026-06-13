"""
User schemas for IAM service.

These schemas define API contracts for:
- User creation
- User updates
- User responses (public-safe)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# =========================================================
# BASE (shared fields)
# =========================================================

class UserBase(BaseModel):
    """
    Shared user fields.
    """
    email: EmailStr = Field(..., max_length=255)


# =========================================================
# CREATE
# =========================================================

class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """
    password: str = Field(..., min_length=8, max_length=128)


# =========================================================
# UPDATE
# =========================================================

class UserUpdate(BaseModel):
    """
    Schema for updating user fields.
    All fields optional.
    """

    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    is_active: bool | None = None
    is_verified: bool | None = None


# =========================================================
# INTERNAL (DB-facing / service layer)
# =========================================================

class UserInDB(BaseModel):
    """
    Internal representation of a user stored in DB.

    NOTE:
    - password_hash is internal only
    - never expose this outside IAM service
    """

    id: uuid.UUID
    email: EmailStr

    password_hash: str

    is_active: bool
    is_verified: bool
    is_superuser: bool

    last_login_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class RoleOut(BaseModel):
    """
    Minimal role representation for API responses.
    """
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileOut(BaseModel):
    """
    Optional profile exposure.
    """
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserOut(UserBase):
    """
    Public API response schema.

    SAFE: no password hash, no internal fields.
    """

    id: uuid.UUID

    is_active: bool
    is_verified: bool
    is_superuser: bool

    last_login_at: datetime | None

    created_at: datetime
    updated_at: datetime

    roles: list[RoleOut] = Field(default_factory=list)
    profile: UserProfileOut | None = None

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# AUTH RESPONSE (optional but useful)
# =========================================================

class TokenOut(BaseModel):
    """
    JWT token response schema.
    """
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """
    Login response combining token + user.
    """
    token: TokenOut
    user: UserOut