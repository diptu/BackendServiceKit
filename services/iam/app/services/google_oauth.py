"""
Google OAuth2 OIDC authentication service.

Authorization Code Flow backend:
  1. generate_auth_url()  — build Google consent URL + store CSRF state token
  2. consume_state()      — validate & single-use-consume the state parameter
  3. exchange_code()      — backend HTTPS POST: code → Google id_token + access_token
  4. verify_id_token()    — RS256 verify Google ID token against cached JWKS
  5. get_or_create_user() — account linking: OAuth match → email merge → new user
"""

from __future__ import annotations

import hashlib
import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

from app.core.config import settings
from app.core.rbac import DEFAULT_ROLE
from app.models.role import Role
from app.models.user import User
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository

# ---------------------------------------------------------------------------
# Module-level state stores  (mirroring the ACTIVE_REFRESH_TOKENS pattern)
# ---------------------------------------------------------------------------

# CSRF protection: sha256(raw_state) → expiry datetime
PENDING_OAUTH_STATES: dict[str, datetime] = {}
_STATE_TTL_MINUTES: int = 10

# Cached Google JWKS — keyed by "data" (dict|None) and "expiry" (datetime|None).
# Using a single dict container avoids module-level reassignment (no `global` needed).
_jwks: dict[str, Any] = {"data": None, "expiry": None}
_JWKS_TTL_MINUTES: int = 60

# Both issuer forms are valid per Google's OIDC spec.
_GOOGLE_ISSUERS: frozenset[str] = frozenset(
    ["accounts.google.com", "https://accounts.google.com"]
)


# ---------------------------------------------------------------------------
# JWKS cache helper (module-level so tests can mock or reset it independently)
# ---------------------------------------------------------------------------


async def _fetch_jwks() -> dict[str, Any]:
    """Return Google's public JWKS, refreshing the in-process cache when stale."""
    now = datetime.now(UTC)
    cached_data = _jwks["data"]
    cached_expiry = _jwks["expiry"]
    if cached_data and cached_expiry and now < cached_expiry:
        return cached_data  # type: ignore[return-value]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.GOOGLE_JWKS_URL)
        resp.raise_for_status()

    _jwks["data"] = resp.json()
    _jwks["expiry"] = now + timedelta(minutes=_JWKS_TTL_MINUTES)
    return _jwks["data"]  # type: ignore[return-value]


def _prune_expired_states() -> None:
    """Evict states that have passed their TTL to bound memory growth."""
    now = datetime.now(UTC)
    expired = [k for k, exp in PENDING_OAUTH_STATES.items() if now >= exp]
    for k in expired:
        del PENDING_OAUTH_STATES[k]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GoogleOAuthService:
    """Orchestrates the full Google OAuth2 Authorization Code Flow."""

    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
    ) -> None:
        self._user_repo = user_repository
        self._role_repo = role_repository

    # ------------------------------------------------------------------
    # Step 1 — generate authorization URL
    # ------------------------------------------------------------------

    def generate_auth_url(self) -> str:
        """
        Build the Google consent-screen URL and persist a CSRF state token.

        The raw state is embedded in the returned URL; the SHA-256 digest is
        stored server-side so the raw value is never held in persistent storage.
        """
        raw_state = secrets.token_urlsafe(32)
        state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
        PENDING_OAUTH_STATES[state_hash] = datetime.now(UTC) + timedelta(
            minutes=_STATE_TTL_MINUTES
        )
        _prune_expired_states()

        qs = urllib.parse.urlencode(
            {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "response_type": "code",
                "scope": "openid email profile",
                "state": raw_state,
                "access_type": "online",
                "prompt": "select_account",
            }
        )
        return f"{settings.GOOGLE_AUTH_URL}?{qs}"

    # ------------------------------------------------------------------
    # Step 2 — validate & consume CSRF state (single-use)
    # ------------------------------------------------------------------

    @staticmethod
    def consume_state(raw_state: str) -> None:
        """
        Validate the state parameter from the Google callback.

        The state hash is popped *before* the expiry check so a concurrent
        replay is always rejected even if it arrives within the TTL window.
        Raises HTTP 400 on any mismatch or expiry.
        """
        state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
        expiry = PENDING_OAUTH_STATES.pop(state_hash, None)
        if expiry is None or datetime.now(UTC) >= expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state parameter.",
            )

    # ------------------------------------------------------------------
    # Step 3 — exchange authorization code for Google tokens
    # ------------------------------------------------------------------

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """
        POST the authorization code to Google's token endpoint (backend-to-backend).

        Returns the raw token response dict which includes ``id_token``.
        Raises HTTP 502 if Google responds with a non-200 status.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                settings.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
        if resp.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to exchange authorization code with Google.",
            )
        return resp.json()

    # ------------------------------------------------------------------
    # Step 4 — verify Google ID token (RS256 + JWKS)
    # ------------------------------------------------------------------

    async def verify_id_token(self, id_token_str: str) -> dict[str, Any]:
        """
        Verify a Google-issued OIDC ID token.

        Uses Google's JWKS endpoint (cached) to validate the RS256 signature,
        and checks ``iss``, ``aud``, and ``exp`` claims.
        Raises HTTP 401 on any verification failure.
        """
        jwks = await _fetch_jwks()
        try:
            payload: dict[str, Any] = jose_jwt.decode(
                id_token_str,
                jwks,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID,
                options={"verify_at_hash": False},
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ID token verification failed.",
            ) from exc

        if payload.get("iss") not in _GOOGLE_ISSUERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer.",
            )
        return payload

    # ------------------------------------------------------------------
    # Step 5 — account linking / user provisioning
    # ------------------------------------------------------------------

    async def get_or_create_user(self, claims: dict[str, Any]) -> User:
        """
        Map verified Google OIDC claims to a local User.

        Linking precedence:
          1. Exact OAuth match  (oauth_provider="google", oauth_id=sub)  → log in
          2. Email match        → link Google account, then log in
             • Rejected if the email is already linked to a *different* Google sub
               (prevents account-takeover via pre-registered email)
          3. No match           → create new verified user with guest role
        """
        google_sub: str = claims["sub"]
        email: str = claims.get("email", "").strip().lower()

        # 1. Exact OAuth match — fast path
        user = await self._user_repo.get_by_oauth_id("google", google_sub)
        if user:
            return await self._user_repo.update_last_login(user)

        # 2. Email match — safe linking
        user = await self._user_repo.get_by_email(email)
        if user:
            if user.oauth_id is not None and user.oauth_id != google_sub:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already linked to a different OAuth account.",
                )
            user = await self._user_repo.set_oauth(user.id, "google", google_sub)
            return await self._user_repo.update_last_login(user)

        # 3. New user — Google already verified the email address
        default_role = await self._role_repo.get_by_slug(DEFAULT_ROLE.value)
        if not default_role:
            default_role = Role(
                slug=DEFAULT_ROLE.value,
                name=DEFAULT_ROLE.value.replace("_", " ").title(),
                is_system=True,
            )
        new_user = User(
            email=email,
            password_hash=None,
            is_active=True,
            is_verified=True,
            is_superuser=False,
            oauth_provider="google",
            oauth_id=google_sub,
            roles=[default_role],
        )
        return await self._user_repo.create(new_user)
