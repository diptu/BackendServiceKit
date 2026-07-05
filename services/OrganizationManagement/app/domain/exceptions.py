"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class OrganizationNotFoundError(Exception):
    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"Organization {organization_id} not found.")
        self.organization_id = organization_id


class OrganizationSlugConflictError(Exception):
    """Raised when a slug is already taken within the same tenant."""

    def __init__(self, tenant_id: UUID, slug: str) -> None:
        super().__init__(
            f"Organization slug '{slug}' is already taken in tenant {tenant_id}."
        )
        self.tenant_id = tenant_id
        self.slug = slug


class OrganizationDeletedError(Exception):
    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"Organization {organization_id} has been deleted.")
        self.organization_id = organization_id


class InvalidOrganizationTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Invalid organization state transition: {from_status} → {to_status}."
        )
        self.from_status = from_status
        self.to_status = to_status


class TenantNotFoundError(Exception):
    """Raised when the tenant_id an organization is created under doesn't exist."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant {tenant_id} not found.")
        self.tenant_id = tenant_id


class TenantServiceUnavailableError(Exception):
    """Raised when Tenent can't be reached to validate a tenant_id."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Could not verify tenant {tenant_id}: Tenent is unreachable.")
        self.tenant_id = tenant_id


class MembershipNotFoundError(Exception):
    def __init__(self, organization_id: UUID, user_id: UUID) -> None:
        super().__init__(
            f"User {user_id} is not a member of organization {organization_id}."
        )
        self.organization_id = organization_id
        self.user_id = user_id


class MembershipAlreadyExistsError(Exception):
    def __init__(self, organization_id: UUID, user_id: UUID) -> None:
        super().__init__(
            f"User {user_id} is already a member of organization {organization_id}."
        )
        self.organization_id = organization_id
        self.user_id = user_id


class TeamNotFoundError(Exception):
    def __init__(self, team_id: UUID) -> None:
        super().__init__(f"Team {team_id} not found.")
        self.team_id = team_id


class TeamNameConflictError(Exception):
    def __init__(self, organization_id: UUID, name: str) -> None:
        super().__init__(
            f"Team '{name}' already exists in organization {organization_id}."
        )
        self.organization_id = organization_id
        self.name = name


class InvalidParentTeamError(Exception):
    """Raised when parent_team_id doesn't belong to the same organization."""

    def __init__(self, parent_team_id: UUID, organization_id: UUID) -> None:
        super().__init__(
            f"Parent team {parent_team_id} does not belong to organization {organization_id}."
        )
        self.parent_team_id = parent_team_id
        self.organization_id = organization_id


class TeamMembershipAlreadyExistsError(Exception):
    def __init__(self, team_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is already a member of team {team_id}.")
        self.team_id = team_id
        self.user_id = user_id


class TeamMembershipNotFoundError(Exception):
    def __init__(self, team_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is not a member of team {team_id}.")
        self.team_id = team_id
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
