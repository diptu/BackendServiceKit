"""Shared response schemas used by more than one entity."""

from __future__ import annotations

from uuid import UUID

from app.schemas.base import AppBaseModel


class UserIdListResponse(AppBaseModel):
    """A plain list of user IDs — used by group-membership listing."""

    items: list[UUID]
    total: int
