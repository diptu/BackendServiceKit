"""Domain exceptions.

InvalidCredentialsError is deliberately the same exception whether the email
is unknown or the password is wrong — the Authentication skill this service
was designed against is explicit: "Never leak authentication failure
details." Callers get one generic 401, always.
"""

from __future__ import annotations

from uuid import UUID


class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


class AccountLockedError(Exception):
    def __init__(self, locked_until_message: str) -> None:
        super().__init__(f"Account is locked. Try again {locked_until_message}.")


class CredentialNotFoundError(Exception):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"No credential set for user {user_id}.")
        self.user_id = user_id


class CredentialAlreadyExistsError(Exception):
    def __init__(self, tenant_id: UUID, email: str) -> None:
        super().__init__(
            f"A credential already exists for '{email}' in tenant {tenant_id}."
        )
        self.tenant_id = tenant_id
        self.email = email


class RefreshTokenInvalidError(Exception):
    """Unknown, expired, or already-revoked refresh token."""

    def __init__(self) -> None:
        super().__init__("Refresh token is invalid or has expired.")


class PasswordResetTokenInvalidError(Exception):
    def __init__(self) -> None:
        super().__init__("Password reset token is invalid or has expired.")


class AccessTokenInvalidError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Access token is invalid: {reason}.")


# ---------------------------------------------------------------------------
# MFA
# ---------------------------------------------------------------------------


class MfaAlreadyEnabledError(Exception):
    def __init__(self) -> None:
        super().__init__("MFA is already enabled for this user.")


class MfaNotEnrolledError(Exception):
    """No MFA secret has been set up (or setup was never confirmed)."""

    def __init__(self) -> None:
        super().__init__("MFA is not enrolled for this user.")


class InvalidMfaCodeError(Exception):
    """Wrong TOTP code, wrong/used recovery code, or an unusable challenge —
    deliberately one exception so a caller cannot tell which was wrong."""

    def __init__(self) -> None:
        super().__init__("Invalid or expired MFA code.")


# ---------------------------------------------------------------------------
# OAuth2.1
# ---------------------------------------------------------------------------


class OAuthClientNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("Unknown OAuth client.")


class OAuthInvalidRequestError(Exception):
    """Any protocol-level rejection of an authorize/token request (bad
    redirect_uri, unsupported grant/response type, PKCE mismatch, invalid or
    expired code, bad client secret). Maps to RFC 6749 error responses."""

    def __init__(self, error: str, description: str) -> None:
        super().__init__(description)
        self.error = error
        self.description = description


# ---------------------------------------------------------------------------
# SSO / OIDC
# ---------------------------------------------------------------------------


class SsoNotConfiguredError(Exception):
    def __init__(self) -> None:
        super().__init__("No OIDC identity provider is configured.")


class SsoStateInvalidError(Exception):
    def __init__(self) -> None:
        super().__init__("SSO state is invalid, already used, or expired.")


class SsoIdentityNotProvisionedError(Exception):
    """The federated identity authenticated at the IdP but has no matching
    local credential to issue tokens for — JIT provisioning against the User
    service is not built yet (see TODO.md)."""

    def __init__(self, email: str) -> None:
        super().__init__(f"No local account is provisioned for '{email}'.")
        self.email = email
