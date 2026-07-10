"""SsoService — federated (OIDC) login as a relying party.

Flow: `begin_login` mints a state+nonce, records them, and returns the IdP
authorization URL to redirect the user to. `complete_login` validates the
returned state (single-use, unexpired), has the injected OidcClient exchange
the code and verify the id_token, then resolves the federated identity to a
LOCAL account.

Identity resolution is deliberately conservative: a returning user is matched
on the stable IdP `subject` via `sso_identities`; a first-time user is matched
to an existing local credential by email and linked. There is no just-in-time
provisioning — if no local account exists, login is refused
(`SsoIdentityNotProvisionedError`) rather than inventing a user_id, because
the User service, not this one, owns identity creation (see TODO.md).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import AuthEventType
from app.domain.exceptions import (
    SsoIdentityNotProvisionedError,
    SsoStateInvalidError,
)
from app.models.auth_event import AuthEvent
from app.models.sso_identity import SsoIdentity
from app.models.sso_state import SsoState
from app.repositories.auth_event import AuthEventRepository
from app.repositories.credential import CredentialRepository
from app.repositories.sso import SsoIdentityRepository, SsoStateRepository
from app.services.oidc_client import OidcClient
from app.services.session_issuer import AuthTokenPair, issue_token_pair


def _as_aware_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class SsoService:
    def __init__(
        self,
        session: AsyncSession,
        oidc_client: OidcClient,
        *,
        provider: str = "default",
    ) -> None:
        self._session = session
        self._client = oidc_client
        self._provider = provider
        self._states = SsoStateRepository(session)
        self._identities = SsoIdentityRepository(session)
        self._credentials = CredentialRepository(session)
        self._events = AuthEventRepository(session)

    async def begin_login(self, tenant_id: uuid.UUID) -> str:
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        await self._states.create(
            SsoState(
                state=state,
                tenant_id=tenant_id,
                provider=self._provider,
                nonce=nonce,
                redirect_uri=self._client.redirect_uri,
                created_at=now,
                expires_at=now + timedelta(seconds=settings.sso_state_ttl_seconds),
            )
        )
        await self._log(tenant_id, None, AuthEventType.SSO_LOGIN_INITIATED)
        return self._client.authorization_url(state=state, nonce=nonce)

    async def complete_login(
        self, tenant_id: uuid.UUID, *, code: str, state: str
    ) -> AuthTokenPair:
        stored = await self._states.get(state, tenant_id=tenant_id)
        now = datetime.now(timezone.utc)
        if (
            stored is None
            or stored.consumed_at is not None
            or _as_aware_utc(stored.expires_at) <= now
        ):
            await self._log(tenant_id, None, AuthEventType.SSO_LOGIN_FAILURE)
            raise SsoStateInvalidError()

        # Single-use: burn the state before the (network) code exchange so a
        # replayed callback can't reuse it even if the exchange races.
        await self._states.consume(state, tenant_id=tenant_id)

        claims = await self._client.exchange_and_verify(
            code=code, redirect_uri=stored.redirect_uri, nonce=stored.nonce
        )

        user_id = await self._resolve_local_user(
            tenant_id, claims["subject"], claims["email"]
        )
        pair = await issue_token_pair(self._session, tenant_id, user_id)
        await self._log(tenant_id, user_id, AuthEventType.SSO_LOGIN_SUCCESS)
        return pair

    async def _resolve_local_user(
        self, tenant_id: uuid.UUID, subject: str, email: str
    ) -> uuid.UUID:
        identity = await self._identities.get_by_subject(
            self._provider, subject, tenant_id=tenant_id
        )
        if identity is not None:
            await self._identities.touch_login(identity)
            return identity.user_id

        credential = await self._credentials.get_by_email(email, tenant_id=tenant_id)
        if credential is None:
            await self._log(tenant_id, None, AuthEventType.SSO_LOGIN_FAILURE)
            raise SsoIdentityNotProvisionedError(email)

        now = datetime.now(timezone.utc)
        await self._identities.create(
            SsoIdentity(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                provider=self._provider,
                subject=subject,
                user_id=credential.user_id,
                email=email,
                created_at=now,
                last_login_at=now,
            )
        )
        return credential.user_id

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
