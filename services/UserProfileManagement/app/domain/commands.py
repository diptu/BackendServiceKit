"""Domain command objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateProfileCmd:
    bio: str | None = None
    pronouns: str | None = None
    display_name_override: str | None = None


@dataclass
class UpdatePreferencesCmd:
    locale: str | None = None
    timezone: str | None = None
    extra: dict[str, object] | None = None


@dataclass
class UpdateContactCmd:
    phone: str | None = None
    secondary_email: str | None = None
    address: dict[str, object] | None = None


@dataclass
class SetAvatarCmd:
    url: str
    content_type: str | None = None
