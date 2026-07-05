"""Pydantic schemas for the Profile resource."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class UpdateProfileRequest(AppBaseModel):
    bio: str | None = Field(None, max_length=2000)
    pronouns: str | None = Field(None, max_length=50)
    display_name_override: str | None = Field(None, max_length=255)


class ProfileResponse(AppBaseModel):
    """created_at/updated_at are None when no row exists yet for this
    user_id — a user who's never touched their profile isn't an error."""

    user_id: UUID
    bio: str | None = None
    pronouns: str | None = None
    display_name_override: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
