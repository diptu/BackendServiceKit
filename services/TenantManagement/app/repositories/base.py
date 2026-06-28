"""Backward-compatibility shim — canonical definition moved to app.infrastructure.repositories.base."""

from app.infrastructure.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)

__all__ = ["BaseRepository", "PageResult", "decode_cursor", "encode_cursor"]
