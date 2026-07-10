"""Import every ORM model so Base.metadata sees all tables.

Required for Alembic autogenerate and the test suite's create_tables fixture.
"""

from __future__ import annotations

from app.models.auth_event import AuthEvent
from app.models.authorization_code import AuthorizationCode
from app.models.credential import Credential
from app.models.mfa_challenge import MfaChallenge
from app.models.mfa_recovery_code import MfaRecoveryCode
from app.models.mfa_secret import MfaSecret
from app.models.oauth_client import OAuthClient
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.sso_identity import SsoIdentity
from app.models.sso_state import SsoState

__all__ = [
    "AuthEvent",
    "AuthorizationCode",
    "Credential",
    "MfaChallenge",
    "MfaRecoveryCode",
    "MfaSecret",
    "OAuthClient",
    "PasswordResetToken",
    "RefreshToken",
    "SsoIdentity",
    "SsoState",
]
