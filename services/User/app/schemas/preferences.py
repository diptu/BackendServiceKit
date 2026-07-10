"""Pydantic schemas for the Preferences resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class UpdatePreferencesRequest(AppBaseModel):
    locale: str | None = Field(None, max_length=35)
    timezone: str | None = Field(None, max_length=64)
    extra: dict[str, Any] | None = None


class PreferencesResponse(AppBaseModel):
    """locale/timezone default to "en"/"UTC" and created_at/updated_at are
    None when no row exists yet for this user_id."""

    user_id: UUID
    locale: str = "en"
    timezone: str = "UTC"
    extra: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
