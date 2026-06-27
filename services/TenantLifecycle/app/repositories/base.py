"""Base repository abstraction."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar("M")


@dataclass
class PageResult(Generic[M]):
    """Result set returned by paginated list operations."""

    items: list[M]
    total: int
    has_more: bool
    next_cursor: str | None = None


def encode_cursor(occurred_at: datetime, entity_id: UUID) -> str:
    """Encode a keyset cursor as a URL-safe base64 string."""
    payload = {"ts": occurred_at.isoformat(), "id": str(entity_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode a cursor string back to (occurred_at, entity_id).

    Raises ValueError for malformed cursors.
    """
    try:
        data: dict[str, str] = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(data["ts"]).replace(tzinfo=timezone.utc), UUID(data["id"])
    except Exception as exc:
        raise ValueError(f"Invalid pagination cursor: {cursor!r}") from exc


class BaseRepository(Generic[M]):
    """Provides session access to all concrete repositories."""

    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
