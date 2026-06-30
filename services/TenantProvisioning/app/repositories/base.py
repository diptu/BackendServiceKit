"""Base repository with cursor-based pagination helpers."""

from __future__ import annotations

import base64
import json
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
    has_more: bool
    next_cursor: str | None


def encode_cursor(created_at: datetime, entity_id: UUID) -> str:
    payload = {"t": created_at.isoformat(), "i": str(entity_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(raw["t"]), UUID(raw["i"])
    except Exception as exc:
        raise ValueError(f"Invalid pagination cursor: {cursor!r}") from exc


class BaseRepository(Generic[M]):
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
