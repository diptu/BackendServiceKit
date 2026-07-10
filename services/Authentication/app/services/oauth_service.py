"""OAuthService — this service acting as an OAuth 2.1 authorization server.

Only the authorization-code grant with PKCE is implemented (the implicit and
password grants are intentionally omitted — OAuth 2.1 removes them). The
resource owner is authenticated the same way every other "current user"
endpoint is: with a Bearer access token this service already issued. That is
a deliberate simplification — a browser deployment would put an interactive
login + consent screen in front of `/oauth/authorize` — but the security
properties of the issued code (single-use, redirect-bound, PKCE-bound,
short-lived) are the real ones.

Tokens minted here go through the same `issue_token_pair` path as password
login, so an OAuth-issued session is introspectable and revocable exactly
like any other.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import AuthEventType
from app.domain.exceptions import OAuthInvalidRequestError
from app.models.auth_event import AuthEvent
from app.models.authorization_code import AuthorizationCode
from app.models.oauth_client import OAuthClient
from app.repositories.auth_event import AuthEventRepository
from app.repositories.oauth import AuthorizationCodeRepository, OAuthClientRepository
from app.services.session_issuer import AuthTokenPair, issue_token_pair
from app.services.token_service import generate_opaque_token, hash_opaque_token


class RegisteredClient:
    __slots__ = ("client_id", "client_secret")

    def __init__(self, client_id: str, client_secret: str | None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _pkce_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _as_aware_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class OAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clients = OAuthClientRepository(session)
        self._codes = AuthorizationCodeRepository(session)
        self._events = AuthEventRepository(session)

    async def register_client(
        self,
        tenant_id: uuid.UUID,
        *,
        name: str,
        redirect_uris: list[str],
        allowed_scopes: list[str] | None,
        is_confidential: bool,
    ) -> RegisteredClient:
        if not redirect_uris:
            raise OAuthInvalidRequestError(
                "invalid_request", "At least one redirect_uri is required."
            )
        client_id = secrets.token_urlsafe(24)
        raw_secret = secrets.token_urlsafe(32) if is_confidential else None
        await self._clients.create(
            OAuthClient(
                client_id=client_id,
                tenant_id=tenant_id,
                name=name,
                is_confidential=is_confidential,
                client_secret_hash=(
                    _hash_secret(raw_secret) if raw_secret is not None else None
                ),
                redirect_uris=redirect_uris,
                allowed_scopes=allowed_scopes or list(settings.oauth_default_scopes),
            )
        )
        await self._log(tenant_id, None, AuthEventType.OAUTH_CLIENT_REGISTERED)
        return RegisteredClient(client_id, raw_secret)

    async def authorize(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        client_id: str,
        redirect_uri: str,
        response_type: str,
        scope: str | None,
        code_challenge: str | None,
        code_challenge_method: str | None,
    ) -> str:
        """Validate an authorization request and return the raw, single-use
        authorization code (the router appends it + state to the redirect)."""
        client = await self._load_client(client_id, tenant_id)

        if response_type != "code":
            raise OAuthInvalidRequestError(
                "unsupported_response_type", "Only response_type=code is supported."
            )
        if redirect_uri not in client.redirect_uris:
            raise OAuthInvalidRequestError(
                "invalid_request", "redirect_uri is not registered for this client."
            )

        granted = self._resolve_scopes(scope, client)

        # PKCE is mandatory for public clients and, per OAuth 2.1, only S256
        # is accepted (the `plain` method is refused).
        if code_challenge is None and not client.is_confidential:
            raise OAuthInvalidRequestError(
                "invalid_request", "code_challenge is required for public clients."
            )
        if code_challenge is not None and (code_challenge_method or "S256") != "S256":
            raise OAuthInvalidRequestError(
                "invalid_request", "Only the S256 code_challenge_method is supported."
            )

        raw_code, code_hash = generate_opaque_token()
        now = datetime.now(timezone.utc)
        await self._codes.create(
            AuthorizationCode(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                code_hash=code_hash,
                client_id=client_id,
                user_id=user_id,
                redirect_uri=redirect_uri,
                scopes=granted,
                code_challenge=code_challenge,
                code_challenge_method="S256" if code_challenge else None,
                created_at=now,
                expires_at=now
                + timedelta(seconds=settings.oauth_authorization_code_ttl_seconds),
            )
        )
        await self._log(tenant_id, user_id, AuthEventType.OAUTH_CODE_ISSUED)
        return raw_code

    async def exchange_code(
        self,
        tenant_id: uuid.UUID,
        *,
        client_id: str,
        client_secret: str | None,
        code: str,
        redirect_uri: str,
        code_verifier: str | None,
    ) -> tuple[AuthTokenPair, list[str]]:
        client = await self._load_client(client_id, tenant_id)
        self._authenticate_client(client, client_secret)

        stored = await self._codes.get_by_hash(
            hash_opaque_token(code), tenant_id=tenant_id
        )
        now = datetime.now(timezone.utc)
        if (
            stored is None
            or stored.consumed_at is not None
            or _as_aware_utc(stored.expires_at) <= now
        ):
            raise OAuthInvalidRequestError(
                "invalid_grant", "Authorization code is invalid or expired."
            )
        if stored.client_id != client_id:
            raise OAuthInvalidRequestError(
                "invalid_grant", "Authorization code was issued to another client."
            )
        if stored.redirect_uri != redirect_uri:
            raise OAuthInvalidRequestError(
                "invalid_grant",
                "redirect_uri does not match the authorization request.",
            )

        if stored.code_challenge is not None:
            if code_verifier is None:
                raise OAuthInvalidRequestError(
                    "invalid_grant", "code_verifier is required (PKCE)."
                )
            if _pkce_s256(code_verifier) != stored.code_challenge:
                raise OAuthInvalidRequestError(
                    "invalid_grant", "PKCE code_verifier does not match."
                )

        # Single-use: consume before minting tokens so a replayed code fails.
        await self._codes.consume(stored.id, tenant_id=tenant_id)
        pair = await issue_token_pair(
            self._session, tenant_id, stored.user_id, scopes=stored.scopes
        )
        await self._log(tenant_id, stored.user_id, AuthEventType.OAUTH_TOKEN_ISSUED)
        return pair, list(stored.scopes)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_client(self, client_id: str, tenant_id: uuid.UUID) -> OAuthClient:
        client = await self._clients.get(client_id)
        if client is None or client.tenant_id != tenant_id:
            raise OAuthInvalidRequestError("invalid_client", "Unknown OAuth client.")
        return client

    def _authenticate_client(
        self, client: OAuthClient, client_secret: str | None
    ) -> None:
        if not client.is_confidential:
            return  # public client — authenticated solely by PKCE
        if (
            client_secret is None
            or client.client_secret_hash is None
            or not secrets.compare_digest(
                _hash_secret(client_secret), client.client_secret_hash
            )
        ):
            raise OAuthInvalidRequestError(
                "invalid_client", "Client authentication failed."
            )

    def _resolve_scopes(self, scope: str | None, client: OAuthClient) -> list[str]:
        if not scope:
            return list(client.allowed_scopes)
        requested = scope.split()
        allowed = set(client.allowed_scopes)
        invalid = [s for s in requested if s not in allowed]
        if invalid:
            raise OAuthInvalidRequestError(
                "invalid_scope",
                f"Scope(s) not allowed for this client: {' '.join(invalid)}.",
            )
        return requested

    async def _log(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        event_type: AuthEventType,
    ) -> None:
        await self._events.create(
            AuthEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                detail=None,
            )
        )
