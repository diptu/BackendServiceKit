"""Wraps a cross-domain in-process call so a genuine bug in another domain
can't crash this domain's aggregation — TODO.md Decision #4's "stronger
guarantee" than the HTTP version had (an HTTP call couldn't accidentally
propagate an unrelated Python exception across the wire the way an
in-process call could)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


async def safe_call(coro: Awaitable[T]) -> T | None:
    try:
        return await coro
    except Exception:
        return None
