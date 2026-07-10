"""OAuth 2.1 authorization-code + PKCE: client registration, authorize,
token exchange, PKCE enforcement, single-use codes, refresh grant."""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery-staple"
REDIRECT_URI = "https://app.example.com/callback"


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


def _auth_headers(tenant_id: uuid.UUID, token: str) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id), "Authorization": f"Bearer {token}"}


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


async def _login(client: AsyncClient, tenant_id: uuid.UUID, email: str) -> str:
    user_id = uuid.uuid4()
    await client.post(
        "/api/v1/auth/credentials",
        json={"user_id": str(user_id), "email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    return str(r.json()["access_token"])


async def _register_client(
    client: AsyncClient,
    tenant_id: uuid.UUID,
    *,
    is_confidential: bool = True,
    scopes: list[str] | None = None,
) -> tuple[str, str | None]:
    r = await client.post(
        "/api/v1/oauth/clients",
        json={
            "name": "Test App",
            "redirect_uris": [REDIRECT_URI],
            "allowed_scopes": scopes or ["openid", "profile"],
            "is_confidential": is_confidential,
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 201
    body = r.json()
    return str(body["client_id"]), body["client_secret"]


async def _authorize(
    client: AsyncClient,
    tenant_id: uuid.UUID,
    token: str,
    client_id: str,
    challenge: str,
) -> str:
    r = await client.get(
        "/api/v1/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "openid",
            "state": "xyz",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        headers=_auth_headers(tenant_id, token),
    )
    assert r.status_code == 302
    location = r.headers["location"]
    query = parse_qs(urlparse(location).query)
    assert query["state"] == ["xyz"]
    return query["code"][0]


@pytest.mark.asyncio
async def test_full_authorization_code_flow(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _login(client, tenant_id, "oauth1@example.com")
    client_id, client_secret = await _register_client(client, tenant_id)
    verifier, challenge = _pkce()

    code = await _authorize(client, tenant_id, token, client_id, challenge)

    r = await client.post(
        "/api/v1/oauth/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": verifier,
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["scope"] == "openid"

    # The issued access token is a normal, introspectable token.
    r = await client.post(
        "/api/v1/auth/introspect",
        json={"token": body["access_token"]},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["active"] is True
    assert r.json()["scopes"] == ["openid"]


@pytest.mark.asyncio
async def test_pkce_mismatch_rejected(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _login(client, tenant_id, "oauth2@example.com")
    client_id, client_secret = await _register_client(client, tenant_id)
    _, challenge = _pkce()
    code = await _authorize(client, tenant_id, token, client_id, challenge)

    r = await client.post(
        "/api/v1/oauth/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": "the-wrong-verifier-entirely",
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_authorization_code_is_single_use(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _login(client, tenant_id, "oauth3@example.com")
    client_id, client_secret = await _register_client(client, tenant_id)
    verifier, challenge = _pkce()
    code = await _authorize(client, tenant_id, token, client_id, challenge)

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": verifier,
    }
    r1 = await client.post(
        "/api/v1/oauth/token", json=payload, headers=_headers(tenant_id)
    )
    assert r1.status_code == 200
    r2 = await client.post(
        "/api/v1/oauth/token", json=payload, headers=_headers(tenant_id)
    )
    assert r2.status_code == 400
    assert r2.json()["detail"]["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_public_client_requires_pkce(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _login(client, tenant_id, "oauth4@example.com")
    client_id, _ = await _register_client(client, tenant_id, is_confidential=False)

    r = await client.get(
        "/api/v1/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
        },
        headers=_auth_headers(tenant_id, token),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "invalid_request"


@pytest.mark.asyncio
async def test_bad_client_secret_rejected(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _login(client, tenant_id, "oauth5@example.com")
    client_id, _ = await _register_client(client, tenant_id)
    verifier, challenge = _pkce()
    code = await _authorize(client, tenant_id, token, client_id, challenge)

    r = await client.post(
        "/api/v1/oauth/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": "wrong-secret",
            "code_verifier": verifier,
        },
        headers=_headers(tenant_id),
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error"] == "invalid_client"


@pytest.mark.asyncio
async def test_authorize_requires_authenticated_owner(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    client_id, _ = await _register_client(client, tenant_id)
    _, challenge = _pkce()
    r = await client.get(
        "/api/v1/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        headers=_headers(tenant_id),  # no Bearer token
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_grant(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    token = await _login(client, tenant_id, "oauth6@example.com")
    client_id, client_secret = await _register_client(client, tenant_id)
    verifier, challenge = _pkce()
    code = await _authorize(client, tenant_id, token, client_id, challenge)
    r = await client.post(
        "/api/v1/oauth/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": verifier,
        },
        headers=_headers(tenant_id),
    )
    refresh_token = r.json()["refresh_token"]

    r = await client.post(
        "/api/v1/oauth/token",
        json={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["refresh_token"]
