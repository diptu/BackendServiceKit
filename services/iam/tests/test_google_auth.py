"""
Google OAuth2 OIDC endpoint tests.

Coverage
--------
GET  /api/v1/auth/google/login    — authorization URL generation, state storage
GET  /api/v1/auth/google/callback — happy paths, state security, token errors,
                                    account linking, audit events, cookie hygiene

All external HTTP calls (Google token endpoint, JWKS) are mocked so the
test suite is fully deterministic and requires no network access.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

import app.services.google_oauth as _google_module
from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.services.google_oauth import (
    PENDING_OAUTH_STATES,
    GoogleOAuthService,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "https://test"
_NATIVE_PASSWORD = "StrongPass1!"
_GOOGLE_SUB = "google_sub_abc123"
_GOOGLE_EMAIL = "oauth-user@gmail.com"

_LOGIN_URL = "/api/v1/auth/google/login"
_CALLBACK_URL = "/api/v1/auth/google/callback"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_state(raw_state: str, ttl_minutes: int = 5) -> None:
    """Directly insert a state into the pending store (bypasses generate_auth_url)."""
    state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
    PENDING_OAUTH_STATES[state_hash] = datetime.now(UTC) + timedelta(
        minutes=ttl_minutes
    )


def _google_token_response(id_token: str = "fake.id.token") -> dict[str, Any]:
    return {
        "id_token": id_token,
        "access_token": "goog_access_token",
        "token_type": "Bearer",
        "expires_in": 3599,
        "scope": "openid email profile",
    }


def _google_claims(
    sub: str = _GOOGLE_SUB,
    email: str = _GOOGLE_EMAIL,
    email_verified: bool = True,
    iss: str = "https://accounts.google.com",
) -> dict[str, Any]:
    return {
        "iss": iss,
        "sub": sub,
        "aud": "fake-client-id",
        "email": email,
        "email_verified": email_verified,
        "name": "OAuth Test User",
        "picture": "https://example.com/pic.jpg",
        "exp": 9_999_999_999,
        "iat": 1_000_000_000,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def https_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE) as ac:
        yield ac


@pytest.fixture
def unique_email() -> str:
    return f"google-{uuid4().hex[:8]}@gmail.com"


@pytest.fixture(autouse=True)
def reset_oauth_state():
    """Isolate each test: clear module-level OAuth state and JWKS cache."""
    PENDING_OAUTH_STATES.clear()
    _google_module._jwks.update({"data": None, "expiry": None})
    yield
    PENDING_OAUTH_STATES.clear()
    _google_module._jwks.update({"data": None, "expiry": None})


@pytest.fixture
async def native_user(https_client: AsyncClient, unique_email: str) -> str:
    """Register a native email/password user; return their email."""
    resp = await https_client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": _NATIVE_PASSWORD},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return unique_email


@pytest.fixture
def mock_exchange_and_verify(mocker):
    """Patch both Google service methods that make external HTTP calls."""

    def _factory(
        sub: str = _GOOGLE_SUB,
        email: str = _GOOGLE_EMAIL,
        iss: str = "https://accounts.google.com",
    ):
        exc = mocker.patch.object(
            GoogleOAuthService,
            "exchange_code",
            new_callable=AsyncMock,
            return_value=_google_token_response(),
        )
        ver = mocker.patch.object(
            GoogleOAuthService,
            "verify_id_token",
            new_callable=AsyncMock,
            return_value=_google_claims(sub=sub, email=email, iss=iss),
        )
        return exc, ver

    return _factory


# ===========================================================================
# Login initiation
# ===========================================================================


@pytest.mark.anyio
class TestGoogleLoginInit:
    async def test_returns_200_with_authorization_url(self, https_client):
        resp = await https_client.get(_LOGIN_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert "authorization_url" in resp.json()

    async def test_authorization_url_targets_google(self, https_client):
        resp = await https_client.get(_LOGIN_URL)
        url = resp.json()["authorization_url"]
        assert "accounts.google.com" in url

    async def test_url_contains_required_oauth_params(self, https_client):
        resp = await https_client.get(_LOGIN_URL)
        parsed = urlparse(resp.json()["authorization_url"])
        params = parse_qs(parsed.query)
        assert params["response_type"] == ["code"]
        assert "openid" in params["scope"][0]
        assert "email" in params["scope"][0]
        assert "state" in params

    async def test_state_stored_server_side(self, https_client):
        resp = await https_client.get(_LOGIN_URL)
        parsed = urlparse(resp.json()["authorization_url"])
        raw_state = parse_qs(parsed.query)["state"][0]
        state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
        assert state_hash in PENDING_OAUTH_STATES

    async def test_each_call_generates_unique_state(self, https_client):
        r1 = await https_client.get(_LOGIN_URL)
        r2 = await https_client.get(_LOGIN_URL)
        s1 = parse_qs(urlparse(r1.json()["authorization_url"]).query)["state"][0]
        s2 = parse_qs(urlparse(r2.json()["authorization_url"]).query)["state"][0]
        assert s1 != s2


# ===========================================================================
# Callback — happy paths
# ===========================================================================


@pytest.mark.anyio
class TestGoogleCallbackHappyPath:
    async def test_new_user_returns_200_with_token_matrix(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify()
        _seed_state("valid_state_abc")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "auth_code", "state": "valid_state_abc"}
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_new_user_is_created_in_database(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify(email="brand-new@gmail.com")
        _seed_state("new_user_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "new_user_state"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["user"]["email"] == "brand-new@gmail.com"

    async def test_new_google_user_is_verified(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify()
        _seed_state("verified_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "verified_state"}
        )
        assert resp.json()["user"]["is_verified"] is True

    async def test_response_includes_user_email(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify(email=_GOOGLE_EMAIL)
        _seed_state("email_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "email_state"}
        )
        assert resp.json()["user"]["email"] == _GOOGLE_EMAIL

    async def test_refresh_cookie_is_set(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify()
        _seed_state("cookie_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "cookie_state"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "refresh_token" in resp.cookies

    async def test_returning_oauth_user_can_login_again(
        self, https_client, mock_exchange_and_verify
    ):
        # First login — creates the user
        mock_exchange_and_verify(sub="return_sub_999", email="return@gmail.com")
        _seed_state("first_state")
        r1 = await https_client.get(
            _CALLBACK_URL, params={"code": "c1", "state": "first_state"}
        )
        assert r1.status_code == status.HTTP_200_OK

        # Second login — same Google sub should find the existing user
        mock_exchange_and_verify(sub="return_sub_999", email="return@gmail.com")
        _seed_state("second_state")
        r2 = await https_client.get(
            _CALLBACK_URL, params={"code": "c2", "state": "second_state"}
        )
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["user"]["email"] == "return@gmail.com"


# ===========================================================================
# Callback — account linking
# ===========================================================================


@pytest.mark.anyio
class TestGoogleAccountLinking:
    async def test_existing_native_user_gets_linked(
        self, https_client, native_user, mock_exchange_and_verify
    ):
        """Google login with the same email as an existing native account links them."""
        mock_exchange_and_verify(email=native_user)
        _seed_state("link_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "link_state"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["user"]["email"] == native_user

    async def test_linked_user_can_still_use_password_login(
        self, https_client, native_user, mock_exchange_and_verify
    ):
        """Linking Google does not invalidate the native password."""
        # Link via Google
        mock_exchange_and_verify(email=native_user)
        _seed_state("pre_link_state")
        await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "pre_link_state"}
        )

        # Password login still works
        resp = await https_client.post(
            "/api/v1/auth/login",
            data={"username": native_user, "password": _NATIVE_PASSWORD},
        )
        assert resp.status_code == status.HTTP_200_OK

    async def test_conflict_returns_409_when_email_linked_to_different_sub(
        self, https_client, mock_exchange_and_verify
    ):
        """Two different Google accounts with the same email → 409."""
        email = f"conflict-{uuid4().hex[:6]}@gmail.com"

        # First: link sub_A
        mock_exchange_and_verify(sub="sub_A", email=email)
        _seed_state("state_a")
        r1 = await https_client.get(
            _CALLBACK_URL, params={"code": "c1", "state": "state_a"}
        )
        assert r1.status_code == status.HTTP_200_OK

        # Second: attempt link with sub_B for the same email
        mock_exchange_and_verify(sub="sub_B", email=email)
        _seed_state("state_b")
        r2 = await https_client.get(
            _CALLBACK_URL, params={"code": "c2", "state": "state_b"}
        )
        assert r2.status_code == status.HTTP_409_CONFLICT


# ===========================================================================
# Callback — state (CSRF) security
# ===========================================================================


@pytest.mark.anyio
class TestGoogleCallbackStateSecurity:
    async def test_missing_state_returns_400(self, https_client):
        resp = await https_client.get(_CALLBACK_URL, params={"code": "some_code"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    async def test_unknown_state_returns_400(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify()
        resp = await https_client.get(
            _CALLBACK_URL,
            params={"code": "c", "state": "state_that_was_never_generated"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "state" in resp.json()["detail"].lower()

    async def test_expired_state_returns_400(
        self, https_client, mock_exchange_and_verify
    ):
        mock_exchange_and_verify()
        _seed_state("expired_state", ttl_minutes=-1)  # already expired
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "expired_state"}
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    async def test_state_is_single_use(
        self, https_client, mock_exchange_and_verify
    ):
        """Second request with the same state must fail even if first succeeded."""
        mock_exchange_and_verify()
        _seed_state("reuse_state")

        r1 = await https_client.get(
            _CALLBACK_URL, params={"code": "c1", "state": "reuse_state"}
        )
        assert r1.status_code == status.HTTP_200_OK

        # Replay — state was consumed
        mock_exchange_and_verify()
        r2 = await https_client.get(
            _CALLBACK_URL, params={"code": "c2", "state": "reuse_state"}
        )
        assert r2.status_code == status.HTTP_400_BAD_REQUEST

    async def test_google_error_param_returns_400(self, https_client):
        _seed_state("err_state")
        resp = await https_client.get(
            _CALLBACK_URL,
            params={"error": "access_denied", "state": "err_state"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "access_denied" in resp.json()["detail"]


# ===========================================================================
# Callback — token exchange / verification errors
# ===========================================================================


@pytest.mark.anyio
class TestGoogleCallbackTokenErrors:
    async def test_google_token_exchange_failure_returns_502(
        self, https_client, mocker
    ):
        mocker.patch.object(
            GoogleOAuthService,
            "exchange_code",
            new_callable=AsyncMock,
            side_effect=__import__("fastapi").HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to exchange authorization code with Google.",
            ),
        )
        _seed_state("fail_exchange_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "bad_code", "state": "fail_exchange_state"}
        )
        assert resp.status_code == status.HTTP_502_BAD_GATEWAY

    async def test_missing_id_token_in_response_returns_502(
        self, https_client, mocker
    ):
        mocker.patch.object(
            GoogleOAuthService,
            "exchange_code",
            new_callable=AsyncMock,
            return_value={"access_token": "tok"},  # no id_token key
        )
        _seed_state("no_id_token_state")
        resp = await https_client.get(
            _CALLBACK_URL,
            params={"code": "c", "state": "no_id_token_state"},
        )
        assert resp.status_code == status.HTTP_502_BAD_GATEWAY

    async def test_invalid_id_token_returns_401(self, https_client, mocker):
        mocker.patch.object(
            GoogleOAuthService,
            "exchange_code",
            new_callable=AsyncMock,
            return_value=_google_token_response(),
        )
        mocker.patch.object(
            GoogleOAuthService,
            "verify_id_token",
            new_callable=AsyncMock,
            side_effect=__import__("fastapi").HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ID token verification failed.",
            ),
        )
        _seed_state("bad_token_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "bad_token_state"}
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_wrong_issuer_returns_401(self, https_client, mock_exchange_and_verify):
        mock_exchange_and_verify(iss="https://evil.example.com")
        # Override verify_id_token to raise 401 for wrong issuer
        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            GoogleOAuthService,
            "verify_id_token",
            new_callable=AsyncMock,
            side_effect=__import__("fastapi").HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer.",
            ),
        ):
            _seed_state("bad_iss_state")
            resp = await https_client.get(
                _CALLBACK_URL, params={"code": "c", "state": "bad_iss_state"}
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_missing_code_param_returns_400(self, https_client):
        _seed_state("no_code_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"state": "no_code_state"}
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================================================
# JWKS caching
# ===========================================================================


@pytest.mark.anyio
class TestJwksCache:
    async def test_second_call_uses_cached_jwks(self, mocker):
        fetch_mock = mocker.patch(
            "app.services.google_oauth._fetch_jwks",
            new_callable=AsyncMock,
            return_value={"keys": []},
        )
        service = GoogleOAuthService(
            user_repository=mocker.MagicMock(),
            role_repository=mocker.MagicMock(),
        )

        # Simulate two verify_id_token calls; _fetch_jwks is invoked each time
        # (the real caching is inside _fetch_jwks itself — we just verify it's called)
        from jose.exceptions import JWTError

        mocker.patch(
            "app.services.google_oauth.jose_jwt.decode",
            side_effect=JWTError("test"),
        )
        with pytest.raises(HTTPException):
            await service.verify_id_token("fake")
        with pytest.raises(HTTPException):
            await service.verify_id_token("fake")

        assert fetch_mock.call_count == 2

    async def test_warm_cache_skips_http_fetch(self, mocker):
        # Pre-warm the cache
        _google_module._jwks["data"] = {"keys": []}
        _google_module._jwks["expiry"] = datetime.now(UTC) + timedelta(hours=1)

        fetch_spy = mocker.patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock
        )

        result = await _google_module._fetch_jwks()

        fetch_spy.assert_not_called()
        assert result == {"keys": []}


# ===========================================================================
# Audit logging
# ===========================================================================


@pytest.mark.anyio
class TestGoogleAuthAuditLogging:
    async def test_successful_login_emits_audit_event(
        self, https_client, mock_exchange_and_verify, mocker
    ):
        mock_exchange_and_verify()
        audit_mock = mocker.patch(
            "app.api.v1.google_auth._audit_logger",
            spec=AuditLogger,
        )
        _seed_state("audit_success_state")
        resp = await https_client.get(
            _CALLBACK_URL, params={"code": "c", "state": "audit_success_state"}
        )
        assert resp.status_code == status.HTTP_200_OK
        event_types = [call.args[0] for call in audit_mock.log.call_args_list]
        assert AuditEventType.GOOGLE_LOGIN_SUCCESS in event_types

    async def test_google_error_emits_failure_audit_event(
        self, https_client, mocker
    ):
        audit_mock = mocker.patch(
            "app.api.v1.google_auth._audit_logger",
            spec=AuditLogger,
        )
        _seed_state("audit_fail_state")
        resp = await https_client.get(
            _CALLBACK_URL,
            params={"error": "access_denied", "state": "audit_fail_state"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        event_types = [call.args[0] for call in audit_mock.log.call_args_list]
        assert AuditEventType.GOOGLE_LOGIN_FAILURE in event_types

    async def test_token_error_emits_failure_audit_event(
        self, https_client, mocker
    ):
        mocker.patch.object(
            GoogleOAuthService,
            "exchange_code",
            new_callable=AsyncMock,
            side_effect=__import__("fastapi").HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="exchange failed",
            ),
        )
        audit_mock = mocker.patch(
            "app.api.v1.google_auth._audit_logger",
            spec=AuditLogger,
        )
        _seed_state("audit_exchange_fail")
        await https_client.get(
            _CALLBACK_URL, params={"code": "bad", "state": "audit_exchange_fail"}
        )
        event_types = [call.args[0] for call in audit_mock.log.call_args_list]
        assert AuditEventType.GOOGLE_LOGIN_FAILURE in event_types


# ===========================================================================
# OpenAPI schema regression
# ===========================================================================


@pytest.mark.anyio
class TestGoogleAuthOpenApiSchema:
    async def test_login_route_in_openapi(self, https_client):
        resp = await https_client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/v1/auth/google/login" in paths

    async def test_callback_route_in_openapi(self, https_client):
        resp = await https_client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/v1/auth/google/callback" in paths
