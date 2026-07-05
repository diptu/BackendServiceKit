"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class RemoteUserNotFoundError(Exception):
    """Raised when UserManagement doesn't have this user."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} not found.")
        self.user_id = user_id


class UserManagementUnavailableError(Exception):
    """Raised when the fail-fast existence check can't get a response at all."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"UserManagement is unreachable (user {user_id}).")
        self.user_id = user_id
