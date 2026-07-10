"""Pydantic schemas for the Avatar resource."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class SetAvatarRequest(AppBaseModel):
    url: str = Field(..., max_length=2048)
    content_type: str | None = Field(None, max_length=100)


class AvatarResponse(AppBaseModel):
    user_id: UUID
    url: str | None = None
    content_type: str | None = None
    uploaded_at: datetime | None = None
