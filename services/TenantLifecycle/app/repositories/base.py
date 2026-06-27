"""Base repository abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar("M")


@dataclass
class PageResult(Generic[M]):
    """Result set returned by paginated list operations."""

    items: list[M]
    total: int
    has_more: bool


class BaseRepository(Generic[M]):
    """Provides session access to all concrete repositories."""

    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
