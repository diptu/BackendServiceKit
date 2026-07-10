"""RS256 asymmetric signing: round-trip, kid header, JWKS publication, and
that a shared-secret verifier cannot validate an asymmetrically-signed token."""

from __future__ import annotations

import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from jose import jwt as jose_jwt  # type: ignore[import-untyped]

from app.core.config import settings
from app.domain.exceptions import AccessTokenInvalidError
from app.services import token_service


def _rsa_keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _use_rs256(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, public_pem = _rsa_keypair()
    monkeypatch.setattr(settings, "jwt_algorithm", "RS256")
    monkeypatch.setattr(settings, "jwt_private_key", private_pem)
    monkeypatch.setattr(settings, "jwt_public_key", public_pem)


def test_rs256_round_trip_and_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_rs256(monkeypatch)
    tenant_id, user_id = uuid.uuid4(), uuid.uuid4()

    token = token_service.create_access_token(tenant_id, user_id, ["openid"])
    claims = token_service.decode_access_token(token)

    assert claims["tenant_id"] == tenant_id
    assert claims["user_id"] == user_id
    assert claims["scopes"] == ["openid"]

    header = jose_jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"
    assert header["kid"]


def test_hs256_secret_cannot_verify_rs256_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_rs256(monkeypatch)
    token = token_service.create_access_token(uuid.uuid4(), uuid.uuid4())

    # Flip verification back to the shared secret — the RS256 token must not
    # validate: only the holder of the public key can verify it.
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    with pytest.raises(AccessTokenInvalidError):
        token_service.decode_access_token(token)


def test_jwks_empty_under_hs256() -> None:
    # Default configuration is HS256 — no key is ever published.
    assert token_service.get_jwks() == {"keys": []}


@pytest.mark.asyncio
async def test_jwks_endpoint_publishes_public_key(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_rs256(monkeypatch)
    r = await client.get("/.well-known/jwks.json")
    assert r.status_code == 200
    keys = r.json()["keys"]
    assert len(keys) == 1
    jwk_entry = keys[0]
    assert jwk_entry["kty"] == "RSA"
    assert jwk_entry["use"] == "sig"
    assert jwk_entry["alg"] == "RS256"
    assert jwk_entry["kid"]
    # Public-key material only — never the private exponent.
    assert "n" in jwk_entry and "e" in jwk_entry
    assert "d" not in jwk_entry
