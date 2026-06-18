"""
Comprehensive test suite for IAM authentication endpoints.

Coverage:
  - Regression: /register and /login (ensure zero regressions)
  - New: /refresh (token rotation, cookie, revocation)
  - New: /logout (revocation, cookie clearing)
  - Audit: AuditLogger called on every relevant path
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.config import settings
from app.models.user import ACTIVE_REFRESH_TOKENS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "https://test"  # https so Secure cookies are honoured by httpx


def _mint_refresh_token(
    user_id: str,
    jti: str | None = None,
    *,
    token_type: str = "refresh",
    expired: bool = False,
) -> str:
    jti = jti or str(uuid4())
    delta = timedelta(seconds=-1) if expired else timedelta(days=7)
    claims: dict[str, Any] = {
        "sub": user_id,
        "jti": jti,
        "roles": [],
        "permissions": [],
        "type": token_type,
        "exp": datetime.now(UTC) + delta,
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _seed_jti(jti: str, user_id: str, *, revoked: bool = False) -> None:
    ACTIVE_REFRESH_TOKENS[jti] = {
        "user_id": user_id,
        "revoked": revoked,
        "expires_at": datetime.now(UTC) + timedelta(days=7),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_token_store():
    """Wipe the in-process refresh-token store before every test."""
    ACTIVE_REFRESH_TOKENS.clear()
    yield
    ACTIVE_REFRESH_TOKENS.clear()


@pytest.fixture
def mock_audit(mocker) -> MagicMock:
    """Replace the module-level AuditLogger with a MagicMock for assertion."""
    mock = MagicMock(spec=AuditLogger)
    mocker.patch("app.api.v1.auth._audit_logger", mock)
    mocker.patch("app.services.auth.AuditLogger", return_value=mock)
    return mock


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid4().hex[:8]}@example.com"


@pytest.fixture
async def https_client(app):
    """HTTPS base-url client so Secure cookies are stored and re-sent."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers that exercise the stack through HTTP
# ---------------------------------------------------------------------------


async def _register(client: AsyncClient, email: str, password: str = "StrongPass1!"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )


async def _login(
    client: AsyncClient,
    email: str,
    password: str = "StrongPass1!",
    *,
    headers: dict[str, str] | None = None,
):
    return await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers=headers or {},
    )


# ===========================================================================
# REGRESSION: /register
# ===========================================================================


class TestRegisterRegression:
    @pytest.mark.anyio
    async def test_register_returns_201_with_user(self, https_client, unique_email):
        response = await _register(https_client, unique_email)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == unique_email
        assert "id" in data
        assert "password_hash" not in data

    @pytest.mark.anyio
    async def test_register_duplicate_email_returns_409(
        self, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        response = await _register(https_client, unique_email)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in response.json()["detail"]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "payload",
        [
            {"password": "StrongPass1!"},
            {"email": "x@example.com"},
        ],
    )
    async def test_register_missing_fields_returns_422(self, https_client, payload):
        response = await https_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# REGRESSION: /login
# ===========================================================================


class TestLoginRegression:
    @pytest.mark.anyio
    async def test_login_returns_token_matrix(self, https_client, unique_email):
        await _register(https_client, unique_email)
        response = await _login(https_client, unique_email)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"].lower() == "bearer"
        assert data["user"]["email"] == unique_email

    @pytest.mark.anyio
    async def test_login_wrong_password_returns_401(self, https_client, unique_email):
        await _register(https_client, unique_email)
        response = await _login(https_client, unique_email, "WrongPass999!")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]

    @pytest.mark.anyio
    async def test_login_unknown_email_returns_401(self, https_client):
        response = await _login(https_client, "ghost@nowhere.com")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_login_empty_credentials_returns_422(self, https_client):
        response = await https_client.post(
            "/api/v1/auth/login", data={"username": "", "password": ""}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.anyio
    async def test_login_sets_httponly_refresh_cookie(self, https_client, unique_email):
        await _register(https_client, unique_email)
        response = await _login(https_client, unique_email)

        assert response.status_code == status.HTTP_200_OK
        set_cookie = response.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie

    @pytest.mark.anyio
    async def test_login_refresh_token_in_active_store(
        self, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        response = await _login(https_client, unique_email)

        refresh_token = response.json()["refresh_token"]
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        jti = payload["jti"]
        assert jti in ACTIVE_REFRESH_TOKENS
        assert not ACTIVE_REFRESH_TOKENS[jti]["revoked"]


# ===========================================================================
# NEW: /refresh
# ===========================================================================


class TestRefreshToken:
    @pytest.mark.anyio
    async def test_refresh_via_body_returns_new_token_pair(
        self, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        old_refresh = login_resp.json()["refresh_token"]

        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != old_refresh

    @pytest.mark.anyio
    async def test_refresh_via_cookie_returns_new_token_pair(
        self, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        await _login(https_client, unique_email)
        # Cookie jar populated by login; httpx re-sends it automatically
        response = await https_client.post("/api/v1/auth/refresh")
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()

    @pytest.mark.anyio
    async def test_refresh_rotates_cookie(self, https_client, unique_email):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        old_cookie = https_client.cookies.get("refresh_token")

        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_resp.json()["refresh_token"]},
        )
        new_cookie_header = response.headers.get("set-cookie", "")
        assert "refresh_token=" in new_cookie_header
        new_value = new_cookie_header.split("refresh_token=")[1].split(";")[0]
        assert new_value != old_cookie

    @pytest.mark.anyio
    async def test_refresh_old_jti_is_revoked_after_rotation(
        self, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        old_refresh = login_resp.json()["refresh_token"]
        old_jti = jwt.decode(
            old_refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )["jti"]

        await https_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )

        assert ACTIVE_REFRESH_TOKENS[old_jti]["revoked"] is True

    @pytest.mark.anyio
    async def test_refresh_replayed_token_returns_401(
        self, app, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        old_refresh = login_resp.json()["refresh_token"]

        transport = ASGITransport(app=app)
        # c1 has no prior cookie — first use consumes the JTI via body
        async with AsyncClient(transport=transport, base_url=_BASE) as c1:
            r1 = await c1.post(
                "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
            )
            assert r1.status_code == status.HTTP_200_OK

        # c2 also has no cookies — body still carries the old (now revoked) JTI
        async with AsyncClient(transport=transport, base_url=_BASE) as c2:
            replay = await c2.post(
                "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
            )

        assert replay.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_refresh_missing_token_returns_401(self, https_client):
        # No cookie, no body
        response = await https_client.post("/api/v1/auth/refresh")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "missing" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_refresh_invalid_jwt_returns_401(self, https_client):
        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.jwt"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_refresh_expired_jwt_returns_401(self, https_client):
        uid = str(uuid4())
        jti = str(uuid4())
        expired_token = _mint_refresh_token(uid, jti, expired=True)
        _seed_jti(jti, uid)

        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_refresh_access_token_type_rejected(self, https_client):
        uid = str(uuid4())
        jti = str(uuid4())
        wrong_type_token = _mint_refresh_token(uid, jti, token_type="access")
        _seed_jti(jti, uid)

        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": wrong_type_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_refresh_pre_revoked_jti_returns_401(self, https_client):
        uid = str(uuid4())
        jti = str(uuid4())
        token = _mint_refresh_token(uid, jti)
        _seed_jti(jti, uid, revoked=True)

        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_refresh_unknown_jti_returns_401(self, https_client):
        uid = str(uuid4())
        jti = str(uuid4())
        token = _mint_refresh_token(uid, jti)
        # JTI deliberately not seeded in ACTIVE_REFRESH_TOKENS

        response = await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# NEW: /logout
# ===========================================================================


class TestLogout:
    @pytest.mark.anyio
    async def test_logout_via_body_returns_204(self, https_client, unique_email):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        refresh = login_resp.json()["refresh_token"]

        response = await https_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.anyio
    async def test_logout_via_cookie(self, https_client, unique_email):
        await _register(https_client, unique_email)
        await _login(https_client, unique_email)

        response = await https_client.post("/api/v1/auth/logout")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.anyio
    async def test_logout_revokes_jti(self, https_client, unique_email):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        refresh = login_resp.json()["refresh_token"]
        jti = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])[
            "jti"
        ]

        await https_client.post("/api/v1/auth/logout", json={"refresh_token": refresh})

        assert ACTIVE_REFRESH_TOKENS[jti]["revoked"] is True

    @pytest.mark.anyio
    async def test_logout_clears_cookie(self, https_client, unique_email):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)

        response = await https_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": login_resp.json()["refresh_token"]},
        )
        set_cookie = response.headers.get("set-cookie", "")
        # FastAPI's delete_cookie sets max-age=0 or expires in the past
        assert "refresh_token=" in set_cookie
        assert (
            "max-age=0" in set_cookie.lower()
            or 'expires="thu, 01 jan 1970' in set_cookie.lower()
        )

    @pytest.mark.anyio
    async def test_logout_double_revoke_returns_401(self, https_client, unique_email):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        refresh = login_resp.json()["refresh_token"]

        await https_client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
        response = await https_client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_logout_missing_token_returns_401(self, https_client):
        response = await https_client.post("/api/v1/auth/logout")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_logout_invalid_jwt_returns_401(self, https_client):
        response = await https_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "garbage.token.here"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_refresh_rejected_after_logout(self, https_client, unique_email):
        """Token revoked via logout must not be refreshable."""
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        refresh = login_resp.json()["refresh_token"]

        await https_client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
        response = await https_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================================================
# AUDIT LOGGING
# ===========================================================================


class TestAuditLogging:
    @pytest.mark.anyio
    async def test_login_success_emits_audit_event(
        self, https_client, unique_email, mocker
    ):
        mock = MagicMock(spec=AuditLogger)
        mocker.patch("app.api.v1.auth._audit_logger", mock)

        await _register(https_client, unique_email)
        await _login(https_client, unique_email)

        mock.log.assert_called()
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.LOGIN_SUCCESS in calls

    @pytest.mark.anyio
    async def test_login_failure_emits_audit_event(
        self, https_client, unique_email, mocker
    ):
        mock = MagicMock(spec=AuditLogger)
        mocker.patch("app.api.v1.auth._audit_logger", mock)

        await _register(https_client, unique_email)
        await _login(https_client, unique_email, "WrongPass999!")

        mock.log.assert_called()
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.LOGIN_FAILURE in calls

    @pytest.mark.anyio
    async def test_refresh_success_emits_audit_event(
        self, https_client, unique_email, mocker
    ):
        mock = MagicMock(spec=AuditLogger)
        mocker.patch("app.api.v1.auth._audit_logger", mock)

        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_resp.json()["refresh_token"]},
        )

        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.TOKEN_REFRESH in calls

    @pytest.mark.anyio
    async def test_refresh_failure_emits_audit_event(self, https_client, mocker):
        mock = MagicMock(spec=AuditLogger)
        mocker.patch("app.api.v1.auth._audit_logger", mock)

        await https_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "bad.token.here"},
        )

        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.TOKEN_REFRESH_FAILURE in calls

    @pytest.mark.anyio
    async def test_logout_emits_audit_event(self, https_client, unique_email, mocker):
        mock = MagicMock(spec=AuditLogger)
        mocker.patch("app.api.v1.auth._audit_logger", mock)

        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        await https_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": login_resp.json()["refresh_token"]},
        )

        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.LOGOUT in calls

    @pytest.mark.anyio
    async def test_audit_captures_ip_and_user_agent(
        self, https_client, unique_email, mocker
    ):
        mock = MagicMock(spec=AuditLogger)
        mocker.patch("app.api.v1.auth._audit_logger", mock)

        await _register(https_client, unique_email)
        await _login(
            https_client,
            unique_email,
            headers={"User-Agent": "TestBrowser/1.0"},
        )

        success_calls = [
            c
            for c in mock.log.call_args_list
            if c.args[0] == AuditEventType.LOGIN_SUCCESS
        ]
        assert success_calls, "Expected a LOGIN_SUCCESS audit call"
        kwargs = success_calls[0].kwargs
        assert kwargs.get("user_agent") == "TestBrowser/1.0"


# ===========================================================================
# OPENAPI SCHEMA — security scheme registration
# ===========================================================================


class TestOpenApiSchema:
    @pytest.mark.anyio
    async def test_openapi_includes_oauth2_security_scheme(self, https_client):
        """OAuth2PasswordBearer must appear in securitySchemes for Authorize to work."""
        response = await https_client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "OAuth2PasswordBearer" in schemes, (
            "securitySchemes missing — Swagger Authorize button will not appear"
        )
        scheme = schemes["OAuth2PasswordBearer"]
        assert scheme["type"] == "oauth2"
        assert "password" in scheme["flows"]
        token_url = scheme["flows"]["password"].get("tokenUrl", "")
        assert "auth/login" in token_url

    @pytest.mark.anyio
    async def test_me_endpoint_carries_security_lock(self, https_client):
        """GET /me must declare the OAuth2 security requirement (lock icon)."""
        response = await https_client.get("/openapi.json")
        schema = response.json()
        me_op = schema["paths"]["/api/v1/auth/me"]["get"]
        security_reqs = me_op.get("security", [])
        assert any("OAuth2PasswordBearer" in req for req in security_reqs), (
            "Lock icon missing — route has no security requirement in OpenAPI spec"
        )

    @pytest.mark.anyio
    async def test_login_endpoint_has_no_security_lock(self, https_client):
        """Login itself must be open — no security requirement on the token endpoint."""
        response = await https_client.get("/openapi.json")
        schema = response.json()
        login_op = schema["paths"]["/api/v1/auth/login"]["post"]
        # An open endpoint either omits 'security' or sets it to [{}]
        security_reqs = login_op.get("security", [])
        assert not any("OAuth2PasswordBearer" in req for req in security_reqs), (
            "Login endpoint must remain open (no Bearer requirement)"
        )


# ===========================================================================
# GET /me — protected profile endpoint
# ===========================================================================


class TestGetMe:
    @pytest.mark.anyio
    async def test_get_me_without_token_returns_401(self, https_client):
        response = await https_client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_get_me_with_access_token_returns_profile(
        self, https_client, unique_email
    ):
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        access_token = login_resp.json()["access_token"]

        response = await https_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == unique_email
        assert "id" in data
        assert "password_hash" not in data

    @pytest.mark.anyio
    async def test_get_me_with_invalid_token_returns_401(self, https_client):
        response = await https_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_get_me_with_refresh_token_type_returns_401(
        self, https_client, unique_email
    ):
        """Refresh tokens must not pass the access-token guard."""
        await _register(https_client, unique_email)
        login_resp = await _login(https_client, unique_email)
        refresh_token = login_resp.json()["refresh_token"]

        response = await https_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
