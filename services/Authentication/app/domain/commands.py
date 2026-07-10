"""Command DTOs — the input side of each service method."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SetCredentialCmd:
    user_id: UUID
    email: str
    password: str


@dataclass(frozen=True)
class LoginCmd:
    email: str
    password: str
    device_info: str | None = None


@dataclass(frozen=True)
class ChangePasswordCmd:
    old_password: str
    new_password: str


@dataclass(frozen=True)
class ResetPasswordCmd:
    token: str
    new_password: str
