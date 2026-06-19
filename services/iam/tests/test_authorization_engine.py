"""
Tests for the authorization engine: JWT context middleware, the
platform-scoped `require_permission` dependency framework, the permission
catalog (define/seed/assign/remove), and the org-scoped permission cache.

Matrices covered:
  - JWT validation happy path + hostile paths (missing/invalid/expired/
    wrong-type token) through both the middleware and the dependency
    fallback path.
  - Permission-based authorization: granted vs. missing scope, with a
    clean HTTP 403 (not a 500/401) on missing scope.
  - Permission catalog: idempotent seeding, assign/remove on roles,
    cross-tenant hostile attempts on those new endpoints.
  - Cache-aside correctness: cache hits short-circuit recomputation, and
    the role-version-embedded key naturally busts stale entries; Redis
    construction failures degrade to the in-memory backend rather than
    crashing the request path.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.v1.dependencies import require_permission
from app.core.cache import (
    InMemoryPermissionCache,
    RedisPermissionCache,
    get_permission_cache,
    reset_permission_cache,
)
from app.core.config import settings
from app.core.rbac import PLATFORM_PERMISSIONS
from app.core.security import create_access_token
from app.db.seed_rbac import seed_rbac_catalog
from app.middleware.authorization import JWTContextMiddleware
from app.models.organization_member import OrganizationMember
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.services.org_permissions import get_member_permissions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mint_token(
    sub: str | UUID,
    *,
    permissions: list[str] | None = None,
    token_type: str = "access",
    expires_delta: timedelta = timedelta(minutes=15),
) -> str:
    return create_access_token(
        data={
            "sub": str(sub),
            "type": token_type,
            "permissions": permissions or [],
        },
        expires_delta=expires_delta,
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


async def _create_org(client, token: str, *, slug: str) -> dict:
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme Inc", "slug": slug},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _add_member(client, token: str, org_id: str, user_id: str, *, role_slug=None):
    payload: dict = {"user_id": user_id}
    if role_slug is not None:
        payload["role_slug"] = role_slug
    return await client.post(
        f"/api/v1/organizations/{org_id}/members", json=payload, headers=_auth(token)
    )


def _build_protected_app() -> FastAPI:
    """
    Minimal standalone app exercising JWTContextMiddleware +
    require_permission end-to-end over real HTTP, without touching any
    production router (the production app intentionally doesn't retrofit
    this onto existing endpoints, to avoid changing their behavior).
    """
    app = FastAPI()
    app.add_middleware(JWTContextMiddleware)

    @app.get("/protected")
    async def protected(
        claims: dict = Depends(require_permission("users:create")),  # noqa: B008
    ) -> dict:
        return {"ok": True, "sub": claims["sub"]}

    return app


@pytest.fixture
async def protected_client():
    transport = ASGITransport(app=_build_protected_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def _seed_rbac(db_session):
    """Idempotent: mirrors the seeding the real app performs at startup."""
    await seed_rbac_catalog(db_session)


@pytest.fixture
async def owner(client):
    return await _register(client, "owner@test.com")


@pytest.fixture
async def member(client):
    return await _register(client, "member@test.com")


@pytest.fixture
async def outsider(client):
    return await _register(client, "outsider@test.com")


@pytest.fixture
async def organization(client, owner):
    return await _create_org(client, _token(owner["id"]), slug="acme")


# ---------------------------------------------------------------------------
# JWT validation: middleware + dependency, happy and hostile paths
# ---------------------------------------------------------------------------


class TestJWTValidation:
    @pytest.mark.anyio
    async def test_valid_token_succeeds(self, protected_client) -> None:
        token = _mint_token(uuid4(), permissions=["users:create"])
        resp = await protected_client.get("/protected", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.anyio
    async def test_missing_token_returns_401(self, protected_client) -> None:
        resp = await protected_client.get("/protected")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_garbage_token_returns_401(self, protected_client) -> None:
        resp = await protected_client.get("/protected", headers=_auth("not-a-real-jwt"))
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_expired_token_returns_401(self, protected_client) -> None:
        token = _mint_token(
            uuid4(),
            permissions=["users:create"],
            expires_delta=timedelta(minutes=-5),
        )
        resp = await protected_client.get("/protected", headers=_auth(token))
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_refresh_token_type_rejected_on_access_route(
        self, protected_client
    ) -> None:
        token = _mint_token(uuid4(), permissions=["users:create"], token_type="refresh")
        resp = await protected_client.get("/protected", headers=_auth(token))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Permission-based authorization (require_permission dependency)
# ---------------------------------------------------------------------------


class TestPermissionBasedAuthorization:
    @pytest.mark.anyio
    async def test_token_with_required_permission_succeeds(
        self, protected_client
    ) -> None:
        token = _mint_token(uuid4(), permissions=["users:create", "users:read"])
        resp = await protected_client.get("/protected", headers=_auth(token))
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_token_missing_required_permission_returns_clean_403(
        self, protected_client
    ) -> None:
        token = _mint_token(uuid4(), permissions=["users:read"])
        resp = await protected_client.get("/protected", headers=_auth(token))
        assert resp.status_code == 403
        body = resp.json()
        assert "detail" in body
        assert "users:create" in body["detail"]

    @pytest.mark.anyio
    async def test_token_with_no_permissions_returns_403(
        self, protected_client
    ) -> None:
        token = _mint_token(uuid4(), permissions=[])
        resp = await protected_client.get("/protected", headers=_auth(token))
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_missing_token_returns_401_not_403(self, protected_client) -> None:
        """Authentication failures must short-circuit before the permission
        check — a missing/bad token is a 401, never a 403."""
        resp = await protected_client.get("/protected")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Permission catalog: seeding (section 6)
# ---------------------------------------------------------------------------


class TestPermissionCatalogSeeding:
    @pytest.mark.anyio
    async def test_seeding_is_idempotent(self, db_session) -> None:
        before = (await db_session.execute(select(Permission))).scalars().all()
        await seed_rbac_catalog(db_session)
        after = (await db_session.execute(select(Permission))).scalars().all()
        assert len(before) == len(after)

    @pytest.mark.anyio
    async def test_super_admin_holds_full_platform_catalog(self, db_session) -> None:
        result = await db_session.execute(
            select(Role).where(
                Role.slug == "super_admin", Role.organization_id.is_(None)
            )
        )
        role = result.scalar_one()
        assert {p.slug for p in role.permissions} == set(PLATFORM_PERMISSIONS.values())

    @pytest.mark.anyio
    async def test_guest_role_holds_no_platform_permissions(self, db_session) -> None:
        result = await db_session.execute(
            select(Role).where(Role.slug == "guest", Role.organization_id.is_(None))
        )
        role = result.scalar_one_or_none()
        if role is None:
            return  # not created until first registration; nothing to assert
        assert {p.slug for p in role.permissions} == set()


# ---------------------------------------------------------------------------
# Permission catalog: assign / remove on roles (section 6) + protection
# ---------------------------------------------------------------------------


class TestRolePermissionAssignment:
    @pytest.mark.anyio
    async def test_superuser_can_assign_permission_to_global_role(
        self, client, owner, db_session
    ) -> None:
        await _make_superuser(db_session, owner["id"])
        token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={"name": "Billing", "slug": "billing-global"},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        role = resp.json()

        resp = await client.post(
            f"/api/v1/roles/{role['id']}/permissions",
            json={"permission_slugs": ["users:read"]},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert "users:read" in {p["slug"] for p in resp.json()["permissions"]}

    @pytest.mark.anyio
    async def test_non_superuser_cannot_assign_permission_to_global_role(
        self, client, owner, db_session
    ) -> None:
        await _make_superuser(db_session, owner["id"])
        su_token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={"name": "Billing2", "slug": "billing-global-2"},
            headers=_auth(su_token),
        )
        role = resp.json()

        plain = await _register(client, "plain@test.com")
        plain_token = _token(plain["id"])
        resp = await client.post(
            f"/api/v1/roles/{role['id']}/permissions",
            json={"permission_slugs": ["users:read"]},
            headers=_auth(plain_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_assign_unknown_permission_slug_returns_404(
        self, client, owner, db_session
    ) -> None:
        await _make_superuser(db_session, owner["id"])
        token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={"name": "Billing3", "slug": "billing-global-3"},
            headers=_auth(token),
        )
        role = resp.json()

        resp = await client.post(
            f"/api/v1/roles/{role['id']}/permissions",
            json={"permission_slugs": ["does-not-exist:anything"]},
            headers=_auth(token),
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_remove_permission_from_role(self, client, owner, db_session) -> None:
        await _make_superuser(db_session, owner["id"])
        token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Billing4",
                "slug": "billing-global-4",
                "permission_slugs": ["users:read", "users:create"],
            },
            headers=_auth(token),
        )
        role = resp.json()
        target = next(p for p in role["permissions"] if p["slug"] == "users:read")

        resp = await client.delete(
            f"/api/v1/roles/{role['id']}/permissions/{target['id']}",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        remaining = {p["slug"] for p in resp.json()["permissions"]}
        assert "users:read" not in remaining
        assert "users:create" in remaining

    @pytest.mark.anyio
    async def test_cannot_assign_permission_to_system_role(
        self, client, owner, db_session
    ) -> None:
        await _make_superuser(db_session, owner["id"])
        token = _token(owner["id"])
        resp = await client.get("/api/v1/roles", headers=_auth(token))
        org_owner_role = next(r for r in resp.json() if r["slug"] == "org_owner")

        resp = await client.post(
            f"/api/v1/roles/{org_owner_role['id']}/permissions",
            json={"permission_slugs": ["users:read"]},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_org_admin_can_assign_permission_to_org_custom_role(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Custom",
                "slug": "custom-role",
                "organization_id": organization["id"],
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 201, resp.text
        role = resp.json()

        await _add_member(
            client, owner_token, organization["id"], member["id"], role_slug="org_admin"
        )
        admin_token = _token(member["id"])
        resp = await client.post(
            f"/api/v1/roles/{role['id']}/permissions",
            json={"permission_slugs": ["organizations:read"]},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.anyio
    async def test_org_member_cannot_assign_permission_to_org_custom_role(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Custom2",
                "slug": "custom-role-2",
                "organization_id": organization["id"],
            },
            headers=_auth(owner_token),
        )
        role = resp.json()

        await _add_member(client, owner_token, organization["id"], member["id"])
        member_token = _token(member["id"])
        resp = await client.post(
            f"/api/v1/roles/{role['id']}/permissions",
            json={"permission_slugs": ["organizations:read"]},
            headers=_auth(member_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_outsider_cannot_assign_permission_to_role_in_org_they_dont_belong_to(
        self, client, organization, owner, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Custom3",
                "slug": "custom-role-3",
                "organization_id": organization["id"],
            },
            headers=_auth(owner_token),
        )
        role = resp.json()

        outsider_token = _token(outsider["id"])
        resp = await client.post(
            f"/api/v1/roles/{role['id']}/permissions",
            json={"permission_slugs": ["organizations:read"]},
            headers=_auth(outsider_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Org-scoped permission cache (section 7 — ACL caching)
# ---------------------------------------------------------------------------


class TestPermissionCache:
    @pytest.fixture(autouse=True)
    def _clean_cache(self):
        reset_permission_cache()
        yield
        reset_permission_cache()

    def _member(
        self, *, permission_slugs: set[str], updated_at: datetime
    ) -> OrganizationMember:
        # Duck-typed stand-in: get_member_permissions only ever touches
        # .user_id / .role.id / .role.updated_at / .role.permissions[*].slug,
        # so a real DB-backed OrganizationMember isn't needed for this test.
        role = SimpleNamespace(
            id=uuid4(),
            updated_at=updated_at,
            permissions=[SimpleNamespace(slug=s) for s in permission_slugs],
        )
        return cast("OrganizationMember", SimpleNamespace(user_id=uuid4(), role=role))

    @pytest.mark.anyio
    async def test_in_memory_cache_round_trip(self) -> None:
        cache = InMemoryPermissionCache()
        await cache.set("k", {"a", "b"}, ttl_seconds=60)
        assert await cache.get("k") == {"a", "b"}

    @pytest.mark.anyio
    async def test_in_memory_cache_expires(self, monkeypatch) -> None:
        cache = InMemoryPermissionCache()
        clock = {"t": 0.0}
        monkeypatch.setattr("app.core.cache.time.monotonic", lambda: clock["t"])

        await cache.set("k", {"a"}, ttl_seconds=10)
        assert await cache.get("k") == {"a"}

        clock["t"] = 11.0
        assert await cache.get("k") is None

    @pytest.mark.anyio
    async def test_cache_hit_avoids_recomputation(self) -> None:
        now = datetime.now(UTC)
        organization_id = uuid4()
        member = self._member(permission_slugs={"organizations:read"}, updated_at=now)

        first = await get_member_permissions(organization_id, member)
        assert first == {"organizations:read"}

        # Mutate the in-memory relationship *without* bumping updated_at —
        # the cache key is unchanged, so the stale (cached) value wins.
        member.role.permissions = []
        second = await get_member_permissions(organization_id, member)
        assert second == {"organizations:read"}

    @pytest.mark.anyio
    async def test_role_version_change_busts_the_cache(self) -> None:
        now = datetime.now(UTC)
        organization_id = uuid4()
        member = self._member(permission_slugs={"organizations:read"}, updated_at=now)

        first = await get_member_permissions(organization_id, member)
        assert first == {"organizations:read"}

        member.role.permissions = []
        member.role.updated_at = now + timedelta(seconds=1)
        second = await get_member_permissions(organization_id, member)
        assert second == set()

    @pytest.mark.anyio
    async def test_redis_construction_failure_falls_back_to_in_memory(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "not a valid redis url")
        cache = get_permission_cache()
        assert isinstance(cache, InMemoryPermissionCache)

    @pytest.mark.anyio
    async def test_redis_url_configured_builds_redis_backend(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        cache = get_permission_cache()
        assert isinstance(cache, RedisPermissionCache)


# ---------------------------------------------------------------------------
# Sanity: cross-tenant administration attempt produces a clean 403, not a
# 500 or a silent 200 — explicit hostile-path requirement.
# ---------------------------------------------------------------------------


class TestHostileCrossTenantAdministration:
    @pytest.mark.anyio
    async def test_outsider_invoking_cross_tenant_admin_action_gets_clean_403(
        self, client, organization, outsider
    ) -> None:
        outsider_token = _token(outsider["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}",
            json={"name": str(uuid.uuid4())},
            headers=_auth(outsider_token),
        )
        assert resp.status_code == 403
        assert "detail" in resp.json()
