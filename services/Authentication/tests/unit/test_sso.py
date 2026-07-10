"""SSO (OIDC): federated login mapped to a local account, state validation,
and refusal to log in an unprovisioned identity — all against a fake IdP so
no network is touched."""

from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_sso_service
from app.infrastructure.database.dependencies import get_db
from app.main import app
from app.services.oidc_client import OidcClaims, OidcClient
from app.services.sso_service import SsoService

PASSWORD = "correct-horse-battery-staple"


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


class FakeOidcClient(OidcClient):
    def __init__(self, subject: str, email: str) -> None:
        self._subject = subject
        self._email = email

    @property
    def redirect_uri(self) -> str:
        return "https://auth.example.com/sso/callback"

    def authorization_url(self, *, state: str, nonce: str) -> str:
        return f"https://idp.example.com/authorize?state={state}&nonce={nonce}"

    async def exchange_and_verify(
        self, *, code: str, redirect_uri: str, nonce: str
    ) -> OidcClaims:
        return OidcClaims(subject=self._subject, email=self._email)


def _install_fake(subject: str, email: str) -> None:
    async def _override(db: AsyncSession = Depends(get_db)) -> SsoService:
        return SsoService(db, FakeOidcClient(subject, email))

    app.dependency_overrides[get_sso_service] = _override


async def _create_credential(
    client: AsyncClient, tenant_id: uuid.UUID, email: str
) -> uuid.UUID:
    user_id = uuid.uuid4()
    r = await client.post(
        "/api/v1/auth/credentials",
        json={"user_id": str(user_id), "email": email, "password": PASSWORD},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 204
    return user_id


async def _begin(client: AsyncClient, tenant_id: uuid.UUID) -> str:
    r = await client.post("/api/v1/sso/login", headers=_headers(tenant_id))
    assert r.status_code == 200
    url = r.json()["authorization_url"]
    return str(parse_qs(urlparse(url).query)["state"][0])


@pytest.mark.asyncio
async def test_federated_login_matches_local_account(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    email = "sso1@example.com"
    await _create_credential(client, tenant_id, email)
    _install_fake("idp-subject-1", email)

    state = await _begin(client, tenant_id)
    r = await client.post(
        "/api/v1/sso/callback",
        json={"code": "any-code", "state": state},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["refresh_token"]


@pytest.mark.asyncio
async def test_unprovisioned_identity_refused(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    _install_fake("idp-subject-2", "stranger@example.com")

    state = await _begin(client, tenant_id)
    r = await client.post(
        "/api/v1/sso/callback",
        json={"code": "any-code", "state": state},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_invalid_state_rejected(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    _install_fake("idp-subject-3", "sso3@example.com")
    await _begin(client, tenant_id)

    r = await client.post(
        "/api/v1/sso/callback",
        json={"code": "any-code", "state": "not-a-real-state"},
        headers=_headers(tenant_id),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_state_is_single_use(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    email = "sso4@example.com"
    await _create_credential(client, tenant_id, email)
    _install_fake("idp-subject-4", email)

    state = await _begin(client, tenant_id)
    payload = {"code": "any-code", "state": state}
    r1 = await client.post(
        "/api/v1/sso/callback", json=payload, headers=_headers(tenant_id)
    )
    assert r1.status_code == 200
    r2 = await client.post(
        "/api/v1/sso/callback", json=payload, headers=_headers(tenant_id)
    )
    assert r2.status_code == 400
