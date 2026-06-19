"""
Section 9 security hardening tests: login rate limiting, account lockout
with exponential backoff, access-token revocation (logout blacklist +
password-change invalidation horizon), security headers, and CORS.

Module-level singletons (`get_rate_limiter()`, `get_token_blacklist()`,
`ACTIVE_REFRESH_TOKENS`) persist across tests in this file unless reset —
the autouse `_reset_security_state` fixture below clears them before and
after every test. This fixture is intentionally local to this file (not
added to the shared `tests/conftest.py`) since no other test file exercises
these stores.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.config import settings
from app.core.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)
from app.core.security import create_access_token, is_authenticated
from app.core.token_blacklist import (
    InMemoryTokenBlacklist,
    RedisTokenBlacklist,
    get_token_blacklist,
    reset_token_blacklist,
)
from app.models.user import ACTIVE_REFRESH_TOKENS, User

_PASSWORD = "StrongPassw0rd!"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_security_state():
    reset_rate_limiter()
    reset_token_blacklist()
    ACTIVE_REFRESH_TOKENS.clear()
    yield
    reset_rate_limiter()
    reset_token_blacklist()
    ACTIVE_REFRESH_TOKENS.clear()


def _build_bare_protected_app() -> FastAPI:
    """
    Minimal app exercising `is_authenticated` directly, without
    JWTContextMiddleware — forces the decode-from-scratch branch rather
    than the middleware-cached-claims fast path, mirroring the pattern in
    test_authorization_engine.py for exercising both call sites.
    """
    app = FastAPI()

    @app.get("/protected")
    async def protected(
        claims: dict = Depends(is_authenticated),
    ) -> dict:
        return {"ok": True, "sub": claims["sub"]}

    return app


@pytest.fixture
async def bare_protected_client():
    transport = ASGITransport(app=_build_bare_protected_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


async def _register(client, email: str, password: str = _PASSWORD) -> dict:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()


async def _login(client, email: str, password: str = _PASSWORD):
    return await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )


async def _me(client, access_token: str):
    return await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )


# ---------------------------------------------------------------------------
# Rate limiter — unit level (deterministic via monkeypatched monotonic clock)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestRateLimiterUnit:
    async def test_allows_up_to_limit_then_blocks(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(3):
            result = await limiter.hit("k", limit=3, window_seconds=60)
            assert result.allowed
        blocked = await limiter.hit("k", limit=3, window_seconds=60)
        assert not blocked.allowed
        assert blocked.retry_after_seconds > 0

    async def test_window_resets_after_expiry(self, monkeypatch) -> None:
        limiter = InMemoryRateLimiter()
        clock = {"t": 0.0}
        monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: clock["t"])

        for _ in range(2):
            assert (await limiter.hit("k", limit=2, window_seconds=10)).allowed
        assert not (await limiter.hit("k", limit=2, window_seconds=10)).allowed

        clock["t"] = 11.0
        assert (await limiter.hit("k", limit=2, window_seconds=10)).allowed

    async def test_keys_are_isolated(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(2):
            assert (await limiter.hit("a", limit=2, window_seconds=60)).allowed
        assert not (await limiter.hit("a", limit=2, window_seconds=60)).allowed
        assert (await limiter.hit("b", limit=2, window_seconds=60)).allowed

    async def test_redis_construction_failure_falls_back_to_in_memory(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "not a valid redis url")
        assert isinstance(get_rate_limiter(), InMemoryRateLimiter)

    async def test_redis_url_configured_builds_redis_backend(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        assert isinstance(get_rate_limiter(), RedisRateLimiter)


# ---------------------------------------------------------------------------
# Login rate limiting — end-to-end through AuthService.login()
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestLoginRateLimitIntegration:
    async def test_exhaustion_returns_429_with_retry_after_and_audit(
        self, client, mocker
    ) -> None:
        mock = mocker.patch("app.api.v1.auth._audit_logger", spec=AuditLogger)
        email = "ratelimit-exhaustion@example.com"

        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            resp = await _login(client, email, "wrong")
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED

        blocked = await _login(client, email, "wrong")
        assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in blocked.headers

        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.RATE_LIMIT_EXCEEDED in calls

    async def test_rate_limit_is_per_email_not_global(self, client) -> None:
        email_a = "ratelimit-a@example.com"
        email_b = "ratelimit-b@example.com"

        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            resp = await _login(client, email_a, "wrong")
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        blocked = await _login(client, email_a, "wrong")
        assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        still_ok = await _login(client, email_b, "wrong")
        assert still_ok.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Account lockout — exponential backoff on repeated failures
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestAccountLockout:
    async def test_failures_below_threshold_stay_401(self, client) -> None:
        email = "lockout-below@example.com"
        await _register(client, email)
        for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD - 1):
            resp = await _login(client, email, "wrong")
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_threshold_failure_locks_account_for_next_attempt(
        self, client
    ) -> None:
        email = "lockout-threshold@example.com"
        await _register(client, email)

        for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD):
            resp = await _login(client, email, "wrong")
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED

        # Locked — even the *correct* password is blocked during the window.
        locked_resp = await _login(client, email, _PASSWORD)
        assert locked_resp.status_code == status.HTTP_423_LOCKED
        assert "Retry-After" in locked_resp.headers

    async def test_lockout_audit_event_emitted_exactly_once(
        self, client, mocker
    ) -> None:
        mock = mocker.patch("app.api.v1.auth._audit_logger", spec=AuditLogger)
        email = "lockout-audit@example.com"
        await _register(client, email)

        for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD):
            await _login(client, email, "wrong")

        calls = [c.args[0] for c in mock.log.call_args_list]
        assert calls.count(AuditEventType.ACCOUNT_LOCKED) == 1

    async def test_successful_login_resets_failed_count(
        self, client, db_session
    ) -> None:
        email = "lockout-reset@example.com"
        await _register(client, email)
        await _login(client, email, "wrong")
        await _login(client, email, "wrong")

        resp = await _login(client, email, _PASSWORD)
        assert resp.status_code == status.HTTP_200_OK

        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert user.failed_login_count == 0
        assert user.locked_until is None

    async def test_unknown_email_never_locks_or_errors(self, client) -> None:
        email = "lockout-ghost@example.com"
        for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD + 2):
            resp = await _login(client, email, "wrong")
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_backoff_doubles_on_subsequent_lockout(
        self, client, db_session
    ) -> None:
        email = "lockout-backoff@example.com"
        await _register(client, email)

        for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD):
            await _login(client, email, "wrong")

        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert user.failed_login_count == settings.ACCOUNT_LOCKOUT_THRESHOLD
        # SQLite returns naive datetimes from DateTime(timezone=True); normalize
        # before comparing against an aware datetime.now(UTC) (see
        # PasswordResetToken.is_valid / AuthService._as_aware_utc for the
        # same pattern in production code).
        locked_until = user.locked_until.replace(tzinfo=UTC)
        first_seconds = (locked_until - datetime.now(UTC)).total_seconds()
        assert 0 < first_seconds <= settings.ACCOUNT_LOCKOUT_BASE_SECONDS

        # Simulate the lockout window having already elapsed (no real sleep
        # needed — the backoff formula only depends on failed_login_count).
        user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
        db_session.add(user)
        await db_session.commit()
        reset_rate_limiter()  # isolate this round from the login rate limit

        await _login(client, email, "wrong")

        # db_session has expire_on_commit=False and already holds this row
        # in its identity map from the queries above — without expiring it,
        # a fresh select() silently returns the stale cached Python object
        # rather than the row the request above just committed.
        db_session.expire_all()
        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert user.failed_login_count == settings.ACCOUNT_LOCKOUT_THRESHOLD + 1
        locked_until = user.locked_until.replace(tzinfo=UTC)
        second_seconds = (locked_until - datetime.now(UTC)).total_seconds()
        expected = settings.ACCOUNT_LOCKOUT_BASE_SECONDS * 2
        assert expected - 2 <= second_seconds <= expected


# ---------------------------------------------------------------------------
# Access-token revocation: logout blacklist + password-change invalidation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestAccessTokenBlacklist:
    async def test_blacklisted_access_token_returns_401_on_me(self, client) -> None:
        email = "blacklist-logout@example.com"
        await _register(client, email)
        tokens = (await _login(client, email)).json()

        logout_resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert logout_resp.status_code == status.HTTP_204_NO_CONTENT

        assert (await _me(client, tokens["access_token"])).status_code == (
            status.HTTP_401_UNAUTHORIZED
        )

    async def test_unrelated_session_unaffected_by_logout(self, client) -> None:
        email = "blacklist-multisession@example.com"
        await _register(client, email)
        session_a = (await _login(client, email)).json()
        session_b = (await _login(client, email)).json()

        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": session_a["refresh_token"]},
            headers={"Authorization": f"Bearer {session_a['access_token']}"},
        )

        resp = await _me(client, session_b["access_token"])
        assert resp.status_code == status.HTTP_200_OK

    async def test_logout_without_authorization_header_still_revokes_refresh(
        self, client
    ) -> None:
        """No access token presented (e.g. client only kept the refresh
        token) must not block the refresh-token revocation."""
        email = "blacklist-no-header@example.com"
        await _register(client, email)
        tokens = (await _login(client, email)).json()

        logout_resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert logout_resp.status_code == status.HTTP_204_NO_CONTENT

        replay = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert replay.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_password_change_invalidates_prior_access_token(self, client) -> None:
        email = "blacklist-pwchange@example.com"
        await _register(client, email)
        old_token = (await _login(client, email)).json()["access_token"]

        change_resp = await client.post(
            "/api/v1/auth/password/change",
            json={"current_password": _PASSWORD, "new_password": "NewStrongPassw0rd!"},
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert change_resp.status_code == status.HTTP_204_NO_CONTENT

        assert (await _me(client, old_token)).status_code == (
            status.HTTP_401_UNAUTHORIZED
        )

        new_login = await _login(client, email, "NewStrongPassw0rd!")
        assert new_login.status_code == status.HTTP_200_OK
        new_token = new_login.json()["access_token"]
        assert (await _me(client, new_token)).status_code == status.HTTP_200_OK

    async def test_password_reset_invalidates_prior_access_token(
        self, client, mocker
    ) -> None:
        email = "blacklist-pwreset@example.com"
        await _register(client, email)
        old_token = (await _login(client, email)).json()["access_token"]

        mock_send = mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        forgot_resp = await client.post(
            "/api/v1/auth/password/forgot", json={"email": email}
        )
        assert forgot_resp.status_code == status.HTTP_202_ACCEPTED
        raw_token = mock_send.call_args[0][1]

        reset_resp = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": raw_token, "new_password": "NewStrongPassw0rd!"},
        )
        assert reset_resp.status_code == status.HTTP_204_NO_CONTENT

        assert (await _me(client, old_token)).status_code == (
            status.HTTP_401_UNAUTHORIZED
        )

    async def test_revocation_enforced_without_middleware_cache(
        self, bare_protected_client
    ) -> None:
        """Same revocation check, exercised on the non-middleware decode
        path (is_authenticated called directly, no cached jwt_claims)."""
        user_id = str(uuid4())
        jti = str(uuid4())
        token = create_access_token(
            data={"sub": user_id, "type": "access", "jti": jti},
            expires_delta=timedelta(minutes=15),
        )

        ok = await bare_protected_client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert ok.status_code == status.HTTP_200_OK

        await get_token_blacklist().add_jti(jti, ttl_seconds=900)

        blocked = await bare_protected_client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert blocked.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Token blacklist — unit level
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestTokenBlacklistUnit:
    async def test_jti_round_trip_and_expiry(self, monkeypatch) -> None:
        blacklist = InMemoryTokenBlacklist()
        clock = {"t": 0.0}
        monkeypatch.setattr(
            "app.core.token_blacklist.time.monotonic", lambda: clock["t"]
        )

        await blacklist.add_jti("abc", ttl_seconds=10)
        assert await blacklist.contains_jti("abc") is True
        clock["t"] = 11.0
        assert await blacklist.contains_jti("abc") is False

    async def test_invalidate_before_round_trip_and_expiry(self, monkeypatch) -> None:
        blacklist = InMemoryTokenBlacklist()
        clock = {"t": 0.0}
        monkeypatch.setattr(
            "app.core.token_blacklist.time.monotonic", lambda: clock["t"]
        )

        await blacklist.set_invalidate_before("user-1", timestamp=100.0, ttl_seconds=10)
        assert await blacklist.get_invalidate_before("user-1") == 100.0
        clock["t"] = 11.0
        assert await blacklist.get_invalidate_before("user-1") is None

    async def test_redis_construction_failure_falls_back_to_in_memory(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "not a valid redis url")
        assert isinstance(get_token_blacklist(), InMemoryTokenBlacklist)

    async def test_redis_url_configured_builds_redis_backend(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        assert isinstance(get_token_blacklist(), RedisTokenBlacklist)


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestSecurityHeaders:
    async def test_headers_present_on_health_check(self, client) -> None:
        resp = await client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    async def test_headers_present_on_404(self, client) -> None:
        resp = await client.get("/api/v1/this-route-does-not-exist")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    async def test_hsts_present_when_cookie_secure_true(
        self, client, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "COOKIE_SECURE", True)
        resp = await client.get("/health")
        assert "Strict-Transport-Security" in resp.headers

    async def test_hsts_absent_when_cookie_secure_false(
        self, client, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "COOKIE_SECURE", False)
        resp = await client.get("/health")
        assert "Strict-Transport-Security" not in resp.headers


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestCors:
    async def test_preflight_allows_configured_origin(self, client) -> None:
        origin = settings.CORS_ALLOWED_ORIGINS[0]
        resp = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers.get("access-control-allow-origin") == origin

    async def test_preflight_rejects_unlisted_origin(self, client) -> None:
        resp = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != (
            "https://evil.example.com"
        )
