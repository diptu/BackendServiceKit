"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class SessionStatus(StrEnum):
    """Derived (not stored) — computed from revoked_at / expires_at."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
