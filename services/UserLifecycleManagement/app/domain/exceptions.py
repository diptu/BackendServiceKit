"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class InvalidLifecycleTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(f"Invalid lifecycle transition: {from_status} → {to_status}.")
        self.from_status = from_status
        self.to_status = to_status


class RemoteUserNotFoundError(Exception):
    """Raised when UserManagement doesn't have this user."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} not found in UserManagement.")
        self.user_id = user_id


class RemoteUserNotDeletedError(Exception):
    """Raised when trying to restore a user UserManagement says isn't deleted."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is not deleted in UserManagement.")
        self.user_id = user_id


class UserManagementUnavailableError(Exception):
    """Raised when a fail-fast call to UserManagement can't get a response at all."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"UserManagement is unreachable (user {user_id}).")
        self.user_id = user_id
