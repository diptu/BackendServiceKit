from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class AuditEventType(StrEnum):
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    TOKEN_REFRESH = "auth.token.refresh"  # noqa: S105
    TOKEN_REFRESH_FAILURE = "auth.token.refresh.failure"  # noqa: S105
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"  # noqa: S105
    PASSWORD_CHANGE_FAILURE = "auth.password.change.failure"  # noqa: S105
    PASSWORD_RESET_REQUESTED = "auth.password.reset.requested"  # noqa: S105
    PASSWORD_RESET_SUCCESS = "auth.password.reset.success"  # noqa: S105
    PASSWORD_RESET_FAILURE = "auth.password.reset.failure"  # noqa: S105
    GOOGLE_LOGIN_SUCCESS = "auth.google.login.success"
    GOOGLE_LOGIN_FAILURE = "auth.google.login.failure"
    GOOGLE_ACCOUNT_LINKED = "auth.google.account.linked"


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
