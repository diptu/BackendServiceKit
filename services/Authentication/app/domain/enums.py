"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class AuthEventType(StrEnum):
    """Audit trail verbs. Never carries passwords, tokens, or OTPs — see
    AuthEvent.detail's docstring for what's safe to record."""

    CREDENTIAL_SET = "credential_set"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_REFRESHED = "token_refreshed"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    MFA_SETUP_STARTED = "mfa_setup_started"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_CHALLENGE_ISSUED = "mfa_challenge_issued"
    MFA_VERIFIED = "mfa_verified"
    MFA_FAILURE = "mfa_failure"
    OAUTH_CLIENT_REGISTERED = "oauth_client_registered"
    OAUTH_CODE_ISSUED = "oauth_code_issued"
    OAUTH_TOKEN_ISSUED = "oauth_token_issued"
    SSO_LOGIN_INITIATED = "sso_login_initiated"
    SSO_LOGIN_SUCCESS = "sso_login_success"
    SSO_LOGIN_FAILURE = "sso_login_failure"
