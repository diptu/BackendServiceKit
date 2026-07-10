"""Token issuance and verification.

Access tokens are short-lived, stateless JWTs carrying (tenant_id, user_id,
scopes) — the exact claim shape Tenent's IsolationService.resolve_context
already expects to decode, so this service is a drop-in issuer for that
existing consumer. Refresh and password-reset tokens are opaque random
strings (secrets.token_urlsafe), hashed at rest — never a JWT — so they can
be revoked server-side, per the Authentication skill's Token Management
principle ("secure refresh tokens", "support revocation").

Signing is algorithm-agnostic: HS256 uses the shared `secret_key`; an
asymmetric family (RS/ES/PS) uses the PEM `jwt_private_key` to sign and
`jwt_public_key` to verify, and tokens then carry a `kid` header so a
verifier can select the right key from `get_jwks()`.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from jose import JWTError, jwk, jwt  # type: ignore[import-untyped]

from app.core.config import settings
from app.domain.exceptions import AccessTokenInvalidError


class AccessTokenClaims(TypedDict):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    scopes: list[str]


def _is_asymmetric(algorithm: str) -> bool:
    return algorithm.upper().startswith(("RS", "ES", "PS"))


def _signing_key() -> str:
    if _is_asymmetric(settings.jwt_algorithm):
        if not settings.jwt_private_key:
            raise RuntimeError(
                "jwt_private_key must be set when jwt_algorithm is asymmetric."
            )
        return settings.jwt_private_key
    return settings.secret_key


def _verification_key() -> str:
    if _is_asymmetric(settings.jwt_algorithm):
        if not settings.jwt_public_key:
            raise RuntimeError(
                "jwt_public_key must be set when jwt_algorithm is asymmetric."
            )
        return settings.jwt_public_key
    return settings.secret_key


def _current_kid() -> str | None:
    """Stable key id derived from the public key — only meaningful for
    asymmetric signing (symmetric secrets are never published in a JWKS)."""
    if not _is_asymmetric(settings.jwt_algorithm) or not settings.jwt_public_key:
        return None
    return hashlib.sha256(settings.jwt_public_key.encode()).hexdigest()[:16]


def create_access_token(
    tenant_id: uuid.UUID, user_id: uuid.UUID, scopes: list[str] | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "sub": str(user_id),
        "scopes": scopes or [],
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    kid = _current_kid()
    headers = {"kid": kid} if kid else None
    result: str = jwt.encode(
        payload,
        _signing_key(),
        algorithm=settings.jwt_algorithm,
        headers=headers,
    )
    return result


def decode_access_token(token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            _verification_key(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise AccessTokenInvalidError(str(exc)) from exc

    if payload.get("type") != "access":
        raise AccessTokenInvalidError("not an access token")

    tenant_id_raw = payload.get("tenant_id")
    user_id_raw = payload.get("user_id")
    if tenant_id_raw is None or user_id_raw is None:
        raise AccessTokenInvalidError("missing tenant_id/user_id claim")

    scopes_raw = payload.get("scopes")
    scopes = [str(s) for s in scopes_raw] if isinstance(scopes_raw, list) else []

    return AccessTokenClaims(
        tenant_id=uuid.UUID(str(tenant_id_raw)),
        user_id=uuid.UUID(str(user_id_raw)),
        scopes=scopes,
    )


def get_jwks() -> dict[str, list[dict[str, Any]]]:
    """Public JSON Web Key Set. Empty under HS256 (a shared secret is never
    published); under an asymmetric algorithm it exposes the single public
    key other services use to verify tokens locally."""
    if not _is_asymmetric(settings.jwt_algorithm) or not settings.jwt_public_key:
        return {"keys": []}
    key_dict = jwk.construct(settings.jwt_public_key, settings.jwt_algorithm).to_dict()
    entry: dict[str, Any] = {
        k: (v.decode() if isinstance(v, bytes) else v) for k, v in key_dict.items()
    }
    entry["use"] = "sig"
    entry["alg"] = settings.jwt_algorithm
    kid = _current_kid()
    if kid:
        entry["kid"] = kid
    return {"keys": [entry]}


def generate_opaque_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hash) — persist only the hash."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_opaque_token(raw)


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
