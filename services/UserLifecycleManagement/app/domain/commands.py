"""Domain command objects."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class TransitionCmd:
    """Shared shape for every simple named transition (activate, onboard,
    deactivate, offboard, suspend, unsuspend, unlock)."""

    reason: str | None = None
    performed_by: UUID | None = None


@dataclass
class LockCmd:
    reason: str | None = None
    locked_by: UUID | None = None


@dataclass
class RestoreCmd:
    performed_by: UUID | None = None
