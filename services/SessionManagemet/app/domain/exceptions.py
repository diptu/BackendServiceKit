"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class SessionNotFoundError(Exception):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found.")
        self.session_id = session_id


class InvalidSessionTokenError(Exception):
    """The presented session token is unknown, expired, or revoked. One
    exception for all three so a caller cannot tell which — no enumeration."""

    def __init__(self) -> None:
        super().__init__("Session token is invalid or has expired.")
