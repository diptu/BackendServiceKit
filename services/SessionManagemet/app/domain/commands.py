"""Command DTOs — the input side of service methods."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreateSessionCmd:
    user_id: UUID
    device_info: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    ttl_seconds: int | None = None  # falls back to settings.session_ttl_seconds
