"""Base repository abstraction — session-holding convention shared across
every service in this repo. PageResult/cursor helpers copied for
consistency even though nothing here needs pagination (every resource in
this service is a 1-row-per-user singleton)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar("M")


@dataclass
class PageResult(Generic[M]):
    items: list[M]
    total: int
    next_cursor: str | None
    has_more: bool


class BaseRepository(Generic[M]):
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session


def encode_cursor(created_at: datetime, entity_id: UUID) -> str:
    import base64
    import json

    payload = {"t": created_at.isoformat(), "i": str(entity_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
