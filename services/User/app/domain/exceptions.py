"""Domain exceptions.

No RemoteUserNotFoundError/UserManagementUnavailableError here — those
existed in UserLifecycleManagement/UserProfileManagement only because of
the HTTP boundary between separate services. Now that everything is one
service in one transaction, a missing user is just UserNotFoundError.
"""

from __future__ import annotations

from uuid import UUID


class UserNotFoundError(Exception):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} not found.")
        self.user_id = user_id


class UserEmailConflictError(Exception):
    """Raised when an email is already taken within the same tenant."""

    def __init__(self, tenant_id: UUID, email: str) -> None:
        super().__init__(f"Email '{email}' is already taken in tenant {tenant_id}.")
        self.tenant_id = tenant_id
        self.email = email


class InvalidUserStatusTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Invalid user status transition: {from_status} → {to_status}."
        )
        self.from_status = from_status
        self.to_status = to_status


class UserNotDeletedError(Exception):
    """Raised when trying to restore a user that isn't soft-deleted."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is not deleted.")
        self.user_id = user_id


class InvitationNotFoundError(Exception):
    def __init__(self, invitation_id: UUID) -> None:
        super().__init__(f"Invitation {invitation_id} not found.")
        self.invitation_id = invitation_id


class InvitationInvalidError(Exception):
    """Raised when an invitation token is unknown, expired, or already resolved."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Invitation is invalid: {reason}.")
        self.reason = reason
