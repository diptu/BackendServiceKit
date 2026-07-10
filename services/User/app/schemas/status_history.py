"""Pydantic schemas for the user status-history (audit trail) endpoint."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.base import AppBaseModel


class UserStatusHistoryResponse(AppBaseModel):
    id: UUID
    user_id: UUID
    action: str
    from_status: str | None
    to_status: str
    reason: str | None
    performed_by: UUID | None
    occurred_at: datetime


class UserStatusHistoryListResponse(AppBaseModel):
    items: list[UserStatusHistoryResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
