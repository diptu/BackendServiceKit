"""Tenant Resolver middleware: subdomain extraction, JWT/subdomain
reconciliation, fail-closed error paths, and end-to-end that the subdomain's
tenant becomes the authoritative X-Tenant-ID forwarded upstream.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.core.config import settings
from app.main import app
from app.middleware.tenant_resolver import (
    TenantMismatchError,
    extract_subdomain,
    reconcile_tenant,
)
from app.services.control_plane_client import (
    ControlPlaneUnavailableError,
    ResolvedTenant,
)

_ACME = "550e8400-e29b-41d4-a716-446655440000"
_OTHER = "660e8400-e29b-41d4-a716-446655440001"
_RESERVED = {"www", "api", "app", "admin"}


# ---------------------------------------------------------------------------
# extract_subdomain (pure)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host,expected",
    [
        ("acme.my-site.com", "acme"),
        ("acme.my-site.com:8080", "acme"),  # port stripped
        ("ACME.My-Site.com", "acme"),  # case-insensitive
        ("team.acme.my-site.com", "team"),  # leftmost label
        ("my-site.com", None),  # apex
        ("www.my-site.com", None),  # reserved
        ("api.my-site.com", None),  # reserved
        ("localhost", None),  # unrelated host
        ("192.168.1.10", None),  # raw IP
        ("acme.other-domain.com", None),  # different base
        (None, None),
    ],
)
def test_extract_subdomain(host: str | None, expected: str | None) -> None:
    assert extract_subdomain(host, "my-site.com", _RESERVED) == expected


def test_extract_subdomain_no_base_domain_configured() -> None:
    assert extract_subdomain("acme.my-site.com", None, _RESERVED) is None


# ---------------------------------------------------------------------------
# reconcile_tenant (pure)
# ---------------------------------------------------------------------------


def test_reconcile_jwt_only() -> None:
    assert reconcile_tenant(_ACME, None) == _ACME


def test_reconcile_subdomain_only() -> None:
    assert reconcile_tenant(None, _ACME) == _ACME


def test_reconcile_agree() -> None:
    assert reconcile_tenant(_ACME, _ACME) == _ACME


def test_reconcile_neither() -> None:
    assert reconcile_tenant(None, None) is None


def test_reconcile_mismatch_raises() -> None:
    with pytest.raises(TenantMismatchError):
        reconcile_tenant(_ACME, _OTHER)


# ---------------------------------------------------------------------------
# Middleware through the app
# ---------------------------------------------------------------------------


class FakeControlPlane:
    def __init__(self, mapping: dict[str, tuple[str, str]], *, unavailable: bool = False) -> None:
        self._mapping = mapping
        self._unavailable = unavailable

    async def resolve_subdomain(self, subdomain: str) -> ResolvedTenant | None:
        if self._unavailable:
            raise ControlPlaneUnavailableError("down")
        entry = self._mapping.get(subdomain)
        if entry is None:
            return None
        tenant_id, status = entry
        return ResolvedTenant(uuid.UUID(tenant_id), status)


def _access_token(tenant_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": tenant_id,
        "user_id": str(uuid.uuid4()),
        "sub": tenant_id,
        "scopes": [],
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "type": "access",
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm))


def _echo_upstream(request: httpx.Request) -> httpx.Response:
    """Every upstream call echoes back the X-Tenant-ID it received."""
    return httpx.Response(200, json={"forwarded_tenant": request.headers.get("x-tenant-id")})


@pytest_asyncio.fixture
async def gw(monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    monkeypatch.setattr(settings, "tenant_resolver_enabled", True)
    monkeypatch.setattr(settings, "gateway_base_domain", "my-site.com")

    app.state.redis = FakeRedis()
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_echo_upstream))
    app.state.control_plane_client = FakeControlPlane(
        {
            "acme": (_ACME, "active"),
            "other": (_OTHER, "active"),
            "frozen": (_ACME, "disabled"),
        }
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client  # type: ignore[misc]

    await app.state.http_client.aclose()
    app.state.http_client = None
    app.state.redis = None
    if hasattr(app.state, "control_plane_client"):
        delattr(app.state, "control_plane_client")


def _host(subdomain: str) -> dict[str, str]:
    return {"host": f"{subdomain}.my-site.com"}


async def test_unknown_subdomain_is_404(gw: AsyncClient) -> None:
    r = await gw.get("/health", headers=_host("ghost"))
    assert r.status_code == 404


async def test_control_plane_unreachable_fails_closed_503(
    gw: AsyncClient,
) -> None:
    app.state.control_plane_client = FakeControlPlane({}, unavailable=True)
    r = await gw.get("/health", headers=_host("acme"))
    assert r.status_code == 503


async def test_inactive_tenant_is_403(gw: AsyncClient) -> None:
    r = await gw.get("/health", headers=_host("frozen"))
    assert r.status_code == 403


async def test_no_subdomain_passes_through(gw: AsyncClient) -> None:
    # Apex host → nothing to resolve → request proceeds normally (liveness
    # /health always 200; /ready probes real deps so isn't a pass-through probe).
    r = await gw.get("/health", headers={"host": "my-site.com"})
    assert r.status_code == 200


async def test_pre_auth_request_forwards_subdomain_tenant(gw: AsyncClient) -> None:
    # /api/v1/auth/* is exempt from JWT — the subdomain becomes the
    # authoritative X-Tenant-ID, which the client cannot spoof.
    r = await gw.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "x"},
        headers=_host("acme"),
    )
    assert r.status_code == 200
    assert r.json()["forwarded_tenant"] == _ACME


async def test_authenticated_matching_tenant_is_forwarded(gw: AsyncClient) -> None:
    headers = {
        "Authorization": f"Bearer {_access_token(_ACME)}",
        **_host("acme"),
    }
    r = await gw.get(f"/api/v1/tenants/{_ACME}", headers=headers)
    assert r.status_code == 200
    assert r.json()["forwarded_tenant"] == _ACME


async def test_authenticated_cross_tenant_subdomain_is_403(gw: AsyncClient) -> None:
    # Valid token for ACME, but pointed at OTHER's subdomain → blocked.
    headers = {
        "Authorization": f"Bearer {_access_token(_ACME)}",
        **_host("other"),
    }
    r = await gw.get(f"/api/v1/tenants/{_ACME}", headers=headers)
    assert r.status_code == 403


async def test_disabled_feature_is_pass_through(
    gw: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tenant_resolver_enabled", False)
    # Even an unknown subdomain is ignored when the resolver is off.
    r = await gw.get("/health", headers=_host("ghost"))
    assert r.status_code == 200
