"""
Password Management endpoint tests.

Coverage:
  - POST /api/v1/auth/password/change  (authenticated)
  - POST /api/v1/auth/password/forgot  (open — enumeration-safe)
  - POST /api/v1/auth/password/reset   (open — single-use token)
  - Audit events for every success/failure path
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.models.password_reset import PasswordResetToken

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "https://test"
_DEFAULT_PASSWORD = "StrongPass1!"
_NEW_PASSWORD = "NewSecurePass99!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def unique_email() -> str:
    return f"pwmgmt-{uuid4().hex[:8]}@example.com"


@pytest.fixture
async def https_client(app):
    """HTTPS base-url so Secure cookies are honoured by httpx."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE) as ac:
        yield ac


@pytest.fixture
async def registered_user(https_client: AsyncClient, unique_email: str) -> str:
    """Registers a user and returns their email."""
    resp = await https_client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": _DEFAULT_PASSWORD},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return unique_email


@pytest.fixture
async def access_token(
    https_client: AsyncClient, registered_user: str
) -> str:
    """Logs in the registered user and returns a fresh access token."""
    resp = await https_client.post(
        "/api/v1/auth/login",
        data={"username": registered_user, "password": _DEFAULT_PASSWORD},
    )
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()["access_token"]


@pytest.fixture
async def issued_reset_token(
    https_client: AsyncClient,
    registered_user: str,
    mocker: Any,
) -> tuple[str, str]:
    """
    Triggers the forgot-password flow with a mocked email service.
    Returns (email, raw_reset_token).
    """
    mock_send = mocker.patch(
        "app.api.v1.password._email_service.send_password_reset",
        new_callable=AsyncMock,
    )

    resp = await https_client.post(
        "/api/v1/auth/password/forgot",
        json={"email": registered_user},
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED

    assert mock_send.called, "Email service must be called for a known user"
    raw_token: str = mock_send.call_args[0][1]
    return registered_user, raw_token


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


async def _change_password(
    client: AsyncClient,
    access_token: str,
    current: str,
    new: str,
) -> Any:
    return await client.post(
        "/api/v1/auth/password/change",
        json={"current_password": current, "new_password": new},
        headers={"Authorization": f"Bearer {access_token}"},
    )


async def _forgot_password(client: AsyncClient, email: str) -> Any:
    return await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )


async def _reset_password(
    client: AsyncClient, token: str, new_password: str
) -> Any:
    return await client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": new_password},
    )


async def _login(
    client: AsyncClient, email: str, password: str
) -> Any:
    return await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


# ===========================================================================
# Change Password
# ===========================================================================


@pytest.mark.anyio
class TestChangePassword:
    async def test_change_password_success_returns_204(
        self, https_client, access_token
    ):
        resp = await _change_password(
            https_client, access_token, _DEFAULT_PASSWORD, _NEW_PASSWORD
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    async def test_new_password_accepted_after_change(
        self, https_client, access_token, registered_user
    ):
        await _change_password(
            https_client, access_token, _DEFAULT_PASSWORD, _NEW_PASSWORD
        )
        resp = await _login(https_client, registered_user, _NEW_PASSWORD)
        assert resp.status_code == status.HTTP_200_OK

    async def test_old_password_rejected_after_change(
        self, https_client, access_token, registered_user
    ):
        await _change_password(
            https_client, access_token, _DEFAULT_PASSWORD, _NEW_PASSWORD
        )
        resp = await _login(https_client, registered_user, _DEFAULT_PASSWORD)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_wrong_current_password_returns_400(
        self, https_client, access_token
    ):
        resp = await _change_password(
            https_client, access_token, "WrongCurrent1!", _NEW_PASSWORD
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "incorrect" in resp.json()["detail"].lower()

    async def test_unauthenticated_request_returns_401(self, https_client):
        resp = await https_client.post(
            "/api/v1/auth/password/change",
            json={"current_password": _DEFAULT_PASSWORD, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_weak_new_password_returns_422(
        self, https_client, access_token
    ):
        resp = await _change_password(
            https_client, access_token, _DEFAULT_PASSWORD, "short"
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_missing_fields_returns_422(self, https_client, access_token):
        resp = await https_client.post(
            "/api/v1/auth/password/change",
            json={"current_password": _DEFAULT_PASSWORD},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Forgot Password
# ===========================================================================


@pytest.mark.anyio
class TestForgotPassword:
    async def test_known_email_returns_202(
        self, https_client, registered_user, mocker
    ):
        mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        resp = await _forgot_password(https_client, registered_user)
        assert resp.status_code == status.HTTP_202_ACCEPTED

    async def test_unknown_email_also_returns_202(self, https_client):
        """Enumeration protection: response must be identical for unknown emails."""
        resp = await _forgot_password(https_client, "ghost@nowhere.example")
        assert resp.status_code == status.HTTP_202_ACCEPTED

    async def test_response_body_is_generic_for_both_cases(
        self, https_client, registered_user, mocker
    ):
        mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        known_resp = await _forgot_password(https_client, registered_user)
        unknown_resp = await _forgot_password(https_client, "ghost@nowhere.example")
        assert known_resp.json()["message"] == unknown_resp.json()["message"]

    async def test_email_sent_for_known_user(
        self, https_client, registered_user, mocker
    ):
        mock_send = mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        await _forgot_password(https_client, registered_user)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == registered_user

    async def test_email_not_sent_for_unknown_user(self, https_client, mocker):
        mock_send = mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        await _forgot_password(https_client, "ghost@nowhere.example")
        mock_send.assert_not_called()

    async def test_invalid_email_format_returns_422(self, https_client):
        resp = await https_client.post(
            "/api/v1/auth/password/forgot",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_reset_token_created_in_db(
        self,
        https_client,
        registered_user,
        db_session: AsyncSession,
        mocker,
    ):
        mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        await _forgot_password(https_client, registered_user)

        from sqlalchemy import select
        stmt = select(PasswordResetToken)
        result = await db_session.execute(stmt)
        tokens = result.scalars().all()
        assert len(tokens) == 1
        assert tokens[0].used_at is None


# ===========================================================================
# Reset Password
# ===========================================================================


@pytest.mark.anyio
class TestResetPassword:
    async def test_valid_token_returns_204(
        self, https_client, issued_reset_token
    ):
        _, raw_token = issued_reset_token
        resp = await _reset_password(https_client, raw_token, _NEW_PASSWORD)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    async def test_can_login_with_new_password_after_reset(
        self, https_client, issued_reset_token
    ):
        email, raw_token = issued_reset_token
        await _reset_password(https_client, raw_token, _NEW_PASSWORD)

        resp = await _login(https_client, email, _NEW_PASSWORD)
        assert resp.status_code == status.HTTP_200_OK

    async def test_old_password_rejected_after_reset(
        self, https_client, issued_reset_token
    ):
        email, raw_token = issued_reset_token
        await _reset_password(https_client, raw_token, _NEW_PASSWORD)

        resp = await _login(https_client, email, _DEFAULT_PASSWORD)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_is_single_use(
        self, https_client, issued_reset_token
    ):
        """Second use of the same token must return 400."""
        _, raw_token = issued_reset_token
        first = await _reset_password(https_client, raw_token, _NEW_PASSWORD)
        assert first.status_code == status.HTTP_204_NO_CONTENT

        second = await _reset_password(https_client, raw_token, "AnotherPass1!")
        assert second.status_code == status.HTTP_400_BAD_REQUEST

    async def test_expired_token_returns_400(
        self,
        https_client,
        registered_user,
        db_session: AsyncSession,
    ):
        """Directly seed an already-expired token and verify it is rejected."""
        from app.repositories.user import UserRepository

        user = await UserRepository(db_session).get_by_email(registered_user)
        assert user is not None

        expired_model, raw_token = PasswordResetToken.generate(
            user.id, ttl_minutes=-1
        )
        db_session.add(expired_model)
        await db_session.commit()

        resp = await _reset_password(https_client, raw_token, _NEW_PASSWORD)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in resp.json()["detail"].lower()

    async def test_invalid_token_returns_400(self, https_client):
        resp = await _reset_password(https_client, "completely-fake-token", _NEW_PASSWORD)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    async def test_tampered_token_returns_400(
        self, https_client, issued_reset_token
    ):
        _, raw_token = issued_reset_token
        tampered = raw_token[:-4] + "XXXX"
        resp = await _reset_password(https_client, tampered, _NEW_PASSWORD)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    async def test_weak_new_password_returns_422(
        self, https_client, issued_reset_token
    ):
        _, raw_token = issued_reset_token
        resp = await _reset_password(https_client, raw_token, "weak")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_missing_token_field_returns_422(self, https_client):
        resp = await https_client.post(
            "/api/v1/auth/password/reset",
            json={"new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_token_marked_used_after_reset(
        self,
        https_client,
        issued_reset_token,
        db_session: AsyncSession,
    ):
        """Confirm used_at is populated in the DB after a successful reset."""
        import hashlib

        from sqlalchemy import select

        _, raw_token = issued_reset_token
        await _reset_password(https_client, raw_token, _NEW_PASSWORD)

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
        result = await db_session.execute(stmt)
        token_row = result.scalar_one_or_none()
        assert token_row is not None
        assert token_row.used_at is not None


# ===========================================================================
# Audit Logging
# ===========================================================================


@pytest.mark.anyio
class TestPasswordAuditLogging:
    async def test_change_password_success_emits_audit_event(
        self, https_client, access_token, mocker
    ):
        mock = mocker.patch(
            "app.api.v1.password._audit_logger",
            spec=AuditLogger,
        )
        await _change_password(
            https_client, access_token, _DEFAULT_PASSWORD, _NEW_PASSWORD
        )
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.PASSWORD_CHANGED in calls

    async def test_change_password_failure_emits_audit_event(
        self, https_client, access_token, mocker
    ):
        mock = mocker.patch(
            "app.api.v1.password._audit_logger",
            spec=AuditLogger,
        )
        await _change_password(
            https_client, access_token, "WrongCurrent1!", _NEW_PASSWORD
        )
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.PASSWORD_CHANGE_FAILURE in calls

    async def test_forgot_password_emits_audit_event(
        self, https_client, registered_user, mocker
    ):
        mocker.patch(
            "app.api.v1.password._email_service.send_password_reset",
            new_callable=AsyncMock,
        )
        mock = mocker.patch(
            "app.api.v1.password._audit_logger",
            spec=AuditLogger,
        )
        await _forgot_password(https_client, registered_user)
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.PASSWORD_RESET_REQUESTED in calls

    async def test_reset_password_success_emits_audit_event(
        self, https_client, issued_reset_token, mocker
    ):
        mock = mocker.patch(
            "app.api.v1.password._audit_logger",
            spec=AuditLogger,
        )
        _, raw_token = issued_reset_token
        await _reset_password(https_client, raw_token, _NEW_PASSWORD)
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.PASSWORD_RESET_SUCCESS in calls

    async def test_reset_password_failure_emits_audit_event(
        self, https_client, mocker
    ):
        mock = mocker.patch(
            "app.api.v1.password._audit_logger",
            spec=AuditLogger,
        )
        await _reset_password(https_client, "bad-token", _NEW_PASSWORD)
        calls = [c.args[0] for c in mock.log.call_args_list]
        assert AuditEventType.PASSWORD_RESET_FAILURE in calls
