"""Base repository abstractions and shared pagination utilities."""

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
    """Cursor-paginated result set returned by list operations."""

    items: list[M]
    total: int
    next_cursor: str | None
    has_more: bool


class BaseRepository(Generic[M]):
    """Provides session access to all concrete repositories."""

    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session


# ---------------------------------------------------------------------------
# Cursor encoding / decoding
# ---------------------------------------------------------------------------
# Cursors encode the (created_at, id) of the last item on a page and are
# used for keyset (seek) pagination, which is stable under concurrent inserts.


def encode_cursor(created_at: datetime, entity_id: UUID) -> str:
    """Encode a keyset cursor as a URL-safe base64 string."""
    payload = {"t": created_at.isoformat(), "i": str(entity_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode a cursor string back to (created_at, entity_id).

    Raises ValueError for malformed cursors.
    """
    try:
        data: dict[str, str] = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(data["t"]), UUID(data["i"])
    except Exception as exc:
        raise ValueError(f"Invalid pagination cursor: {cursor!r}") from exc
