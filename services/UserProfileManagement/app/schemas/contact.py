"""Pydantic schemas for the Contact Info resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class UpdateContactRequest(AppBaseModel):
    phone: str | None = Field(None, max_length=50)
    secondary_email: str | None = Field(None, max_length=255)
    address: dict[str, Any] | None = None


class ContactResponse(AppBaseModel):
    user_id: UUID
    phone: str | None = None
    secondary_email: str | None = None
    address: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
