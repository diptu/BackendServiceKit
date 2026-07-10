"""Verifies the Authentication service's access tokens locally.

This is the fix for the gateway's biggest production-readiness finding:
before this module existed, ProxyService.forward() read `X-Tenant-ID`
straight off the incoming request and forwarded it verbatim — a client
could set that header to any tenant it wanted, and every downstream
service's tenant-scoping check was enforcing a boundary the caller could
simply declare its way around.

Verification happens locally (shared-secret HS256 decode), not by calling
Authentication's own /introspect endpoint over HTTP, for the same reason
Tenent's IsolationService.resolve_context already decodes these tokens
itself: an extra network round-trip per proxied request would be a real
latency/availability cost for zero additional security once the secret is
shared. See services/Authentication/TODO.md for the plan to move this to
asymmetric (RS256) signing so services only ever need the public key.
"""

from __future__ import annotations

import uuid
from typing import TypedDict

from jose import JWTError, jwt  # type: ignore[import-untyped]

from app.core.config import settings
from app.domain.exceptions import GatewayTokenInvalidError


class VerifiedIdentity(TypedDict):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    scopes: list[str]


def verify_access_token(token: str) -> VerifiedIdentity:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise GatewayTokenInvalidError(str(exc)) from exc

    if payload.get("type") != "access":
        raise GatewayTokenInvalidError("not an access token")

    tenant_id_raw = payload.get("tenant_id")
    user_id_raw = payload.get("user_id")
    if tenant_id_raw is None or user_id_raw is None:
        raise GatewayTokenInvalidError("missing tenant_id/user_id claim")

    scopes_raw = payload.get("scopes")
    scopes = [str(s) for s in scopes_raw] if isinstance(scopes_raw, list) else []

    try:
        return VerifiedIdentity(
            tenant_id=uuid.UUID(str(tenant_id_raw)),
            user_id=uuid.UUID(str(user_id_raw)),
            scopes=scopes,
        )
    except ValueError as exc:
        raise GatewayTokenInvalidError("malformed tenant_id/user_id claim") from exc
