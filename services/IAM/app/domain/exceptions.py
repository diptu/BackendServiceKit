"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class UserNotFoundError(Exception):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} not found.")
        self.user_id = user_id


class RoleNotFoundError(Exception):
    def __init__(self, role_id: UUID) -> None:
        super().__init__(f"Role {role_id} not found.")
        self.role_id = role_id


class RoleNameConflictError(Exception):
    def __init__(self, tenant_id: UUID, name: str) -> None:
        super().__init__(f"Role '{name}' already exists in tenant {tenant_id}.")
        self.tenant_id = tenant_id
        self.name = name


class PermissionNotFoundError(Exception):
    def __init__(self, permission_id: UUID) -> None:
        super().__init__(f"Permission {permission_id} not found.")
        self.permission_id = permission_id


class PermissionNameConflictError(Exception):
    def __init__(self, tenant_id: UUID, name: str) -> None:
        super().__init__(f"Permission '{name}' already exists in tenant {tenant_id}.")
        self.tenant_id = tenant_id
        self.name = name


class RolePermissionAlreadyAssignedError(Exception):
    def __init__(self, role_id: UUID, permission_id: UUID) -> None:
        super().__init__(
            f"Permission {permission_id} is already assigned to role {role_id}."
        )
        self.role_id = role_id
        self.permission_id = permission_id


class RolePermissionNotAssignedError(Exception):
    def __init__(self, role_id: UUID, permission_id: UUID) -> None:
        super().__init__(
            f"Permission {permission_id} is not assigned to role {role_id}."
        )
        self.role_id = role_id
        self.permission_id = permission_id


class UserRoleAlreadyAssignedError(Exception):
    def __init__(self, user_id: UUID, role_id: UUID) -> None:
        super().__init__(f"Role {role_id} is already assigned to user {user_id}.")
        self.user_id = user_id
        self.role_id = role_id


class UserRoleNotAssignedError(Exception):
    def __init__(self, user_id: UUID, role_id: UUID) -> None:
        super().__init__(f"Role {role_id} is not assigned to user {user_id}.")
        self.user_id = user_id
        self.role_id = role_id


class GroupNotFoundError(Exception):
    def __init__(self, group_id: UUID) -> None:
        super().__init__(f"Group {group_id} not found.")
        self.group_id = group_id


class GroupNameConflictError(Exception):
    def __init__(self, tenant_id: UUID, name: str) -> None:
        super().__init__(f"Group '{name}' already exists in tenant {tenant_id}.")
        self.tenant_id = tenant_id
        self.name = name


class GroupMembershipAlreadyExistsError(Exception):
    def __init__(self, group_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is already a member of group {group_id}.")
        self.group_id = group_id
        self.user_id = user_id


class GroupMembershipNotFoundError(Exception):
    def __init__(self, group_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is not a member of group {group_id}.")
        self.group_id = group_id
        self.user_id = user_id


class TenantMembershipAlreadyExistsError(Exception):
    def __init__(self, tenant_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is already a member of tenant {tenant_id}.")
        self.tenant_id = tenant_id
        self.user_id = user_id


class TenantMembershipNotFoundError(Exception):
    def __init__(self, tenant_id: UUID, user_id: UUID) -> None:
        super().__init__(f"User {user_id} is not a member of tenant {tenant_id}.")
        self.tenant_id = tenant_id
        self.user_id = user_id


class AttributeNotFoundError(Exception):
    def __init__(self, attribute_id: UUID) -> None:
        super().__init__(f"Attribute {attribute_id} not found.")
        self.attribute_id = attribute_id


class AttributeKeyConflictError(Exception):
    def __init__(self, user_id: UUID, key: str) -> None:
        super().__init__(f"Attribute '{key}' already exists for user {user_id}.")
        self.user_id = user_id
        self.key = key


class EntitlementNotFoundError(Exception):
    def __init__(self, entitlement_id: UUID) -> None:
        super().__init__(f"Entitlement {entitlement_id} not found.")
        self.entitlement_id = entitlement_id


class AccessReviewNotFoundError(Exception):
    def __init__(self, access_review_id: UUID) -> None:
        super().__init__(f"Access review {access_review_id} not found.")
        self.access_review_id = access_review_id
