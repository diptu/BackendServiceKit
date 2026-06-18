"""Tests for user management endpoints (CRUD, profile, activate/deactivate, search)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token(user_id: UUID | str) -> str:
    return create_access_token(
        data={"sub": str(user_id), "type": "access"},
        expires_delta=timedelta(minutes=15),
    )


async def _register(client, email: str, password: str = "Password123!") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_superuser(db_session, user_id: UUID | str) -> None:
    result = await db_session.execute(select(User).where(User.id == UUID(str(user_id))))
    user = result.scalar_one()
    user.is_superuser = True
    db_session.add(user)
    await db_session.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def regular_user(client):
    """Guest user (no special roles)."""
    return await _register(client, "regular@test.com")


@pytest.fixture
async def admin_user(client, db_session):
    """Superuser — passes require_admin gate."""
    data = await _register(client, "admin@test.com")
    await _make_superuser(db_session, data["id"])
    return data


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


class TestGetMe:
    @pytest.mark.anyio
    async def test_returns_own_profile(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "regular@test.com"

    @pytest.mark.anyio
    async def test_unauthenticated_returns_401(self, client) -> None:
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /users  (admin only)
# ---------------------------------------------------------------------------


class TestListUsers:
    @pytest.mark.anyio
    async def test_admin_can_list_users(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 2

    @pytest.mark.anyio
    async def test_non_admin_gets_403(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_search_by_email(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.get(
            "/api/v1/users?q=regular",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all("regular" in u["email"] for u in items)

    @pytest.mark.anyio
    async def test_filter_is_active(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.get(
            "/api/v1/users?is_active=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(u["is_active"] for u in items)

    @pytest.mark.anyio
    async def test_pagination_page_size(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.get(
            "/api/v1/users?page=1&page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["page_size"] == 1


# ---------------------------------------------------------------------------
# GET /users/{id}
# ---------------------------------------------------------------------------


class TestGetUser:
    @pytest.mark.anyio
    async def test_admin_can_get_any_user(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.get(
            f"/api/v1/users/{regular_user['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == regular_user["id"]

    @pytest.mark.anyio
    async def test_user_can_get_own_record(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.get(
            f"/api/v1/users/{regular_user['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_user_cannot_get_other_user(self, client, regular_user, admin_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.get(
            f"/api/v1/users/{admin_user['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_returns_404_for_unknown_user(self, client, admin_user) -> None:
        import uuid

        token = _token(admin_user["id"])
        resp = await client.get(
            f"/api/v1/users/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /users/{id}  (admin only)
# ---------------------------------------------------------------------------


class TestUpdateUser:
    @pytest.mark.anyio
    async def test_admin_can_deactivate_user(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.patch(
            f"/api/v1/users/{regular_user['id']}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.anyio
    async def test_admin_can_verify_user(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.patch(
            f"/api/v1/users/{regular_user['id']}",
            json={"is_verified": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    @pytest.mark.anyio
    async def test_non_admin_gets_403(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.patch(
            f"/api/v1/users/{regular_user['id']}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /users/{id}/activate  and  /deactivate
# ---------------------------------------------------------------------------


class TestActivateDeactivate:
    @pytest.mark.anyio
    async def test_deactivate_then_activate(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])

        resp = await client.post(
            f"/api/v1/users/{regular_user['id']}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        resp = await client.post(
            f"/api/v1/users/{regular_user['id']}/activate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @pytest.mark.anyio
    async def test_non_admin_cannot_deactivate(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.post(
            f"/api/v1/users/{regular_user['id']}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /users/{id}/profile  and  PATCH /users/{id}/profile
# ---------------------------------------------------------------------------


class TestUserProfile:
    @pytest.mark.anyio
    async def test_get_own_profile_returns_404_when_not_created(
        self, client, regular_user
    ) -> None:
        token = _token(regular_user["id"])
        resp = await client.get(
            f"/api/v1/users/{regular_user['id']}/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_upsert_creates_profile(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        resp = await client.patch(
            f"/api/v1/users/{regular_user['id']}/profile",
            json={"full_name": "Test User", "bio": "Hello world"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["full_name"] == "Test User"
        assert body["bio"] == "Hello world"

    @pytest.mark.anyio
    async def test_upsert_updates_existing_profile(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        uid = regular_user["id"]

        await client.patch(
            f"/api/v1/users/{uid}/profile",
            json={"full_name": "Original Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.patch(
            f"/api/v1/users/{uid}/profile",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    @pytest.mark.anyio
    async def test_get_profile_after_upsert(self, client, regular_user) -> None:
        token = _token(regular_user["id"])
        uid = regular_user["id"]

        await client.patch(
            f"/api/v1/users/{uid}/profile",
            json={"full_name": "Get Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            f"/api/v1/users/{uid}/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Get Test"

    @pytest.mark.anyio
    async def test_user_cannot_update_other_profile(
        self, client, regular_user, admin_user
    ) -> None:
        token = _token(regular_user["id"])
        resp = await client.patch(
            f"/api/v1/users/{admin_user['id']}/profile",
            json={"full_name": "Hacker"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_admin_can_update_any_profile(self, client, admin_user, regular_user) -> None:
        token = _token(admin_user["id"])
        resp = await client.patch(
            f"/api/v1/users/{regular_user['id']}/profile",
            json={"full_name": "Admin Set Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Admin Set Name"
