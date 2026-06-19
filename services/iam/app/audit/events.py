from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AuditEventType(StrEnum):
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    TOKEN_REFRESH = "auth.token.refresh"  # noqa: S105
    TOKEN_REFRESH_FAILURE = "auth.token.refresh.failure"  # noqa: S105
    LOGOUT = "auth.logout"
    TOKEN_REVOKED = "auth.token.revoked"  # noqa: S105
    PASSWORD_CHANGED = "auth.password.changed"  # noqa: S105
    PASSWORD_CHANGE_FAILURE = "auth.password.change.failure"  # noqa: S105
    PASSWORD_RESET_REQUESTED = "auth.password.reset.requested"  # noqa: S105
    PASSWORD_RESET_SUCCESS = "auth.password.reset.success"  # noqa: S105
    PASSWORD_RESET_FAILURE = "auth.password.reset.failure"  # noqa: S105
    GOOGLE_LOGIN_SUCCESS = "auth.google.login.success"
    GOOGLE_LOGIN_FAILURE = "auth.google.login.failure"
    GOOGLE_ACCOUNT_LINKED = "auth.google.account.linked"

    # RBAC mutations (section 8: role assignments / permission updates)
    ORG_MEMBER_ADDED = "rbac.org_member.added"
    ORG_MEMBER_REMOVED = "rbac.org_member.removed"
    ORG_MEMBER_ROLE_ASSIGNED = "rbac.org_member.role_assigned"
    ROLE_CREATED = "rbac.role.created"
    ROLE_UPDATED = "rbac.role.updated"
    ROLE_DELETED = "rbac.role.deleted"
    PERMISSION_ASSIGNED = "rbac.permission.assigned"
    PERMISSION_REMOVED = "rbac.permission.removed"

    # Security (section 9)
    ACCOUNT_LOCKED = "security.account.locked"
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"  # noqa: S105


@dataclass(slots=True)
class AuditEvent:
    event_type: AuditEventType
    timestamp: datetime
    email: str | None = field(default=None)
    ip_address: str | None = field(default=None)
    user_agent: str | None = field(default=None)
    user_id: str | None = field(default=None)
    jti: str | None = field(default=None)
    detail: str | None = field(default=None)
    # Structured resource delta (e.g. {"role_before": "...", "role_after": "..."})
    metadata: dict[str, Any] | None = field(default=None)
