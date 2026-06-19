"""
Tests for Organization Management (multi-tenancy) and Role Management (RBAC).

Covers happy paths plus explicit unauthorized cross-tenant and
unauthorized-role-grant access vectors:
  - acting on an organization the caller doesn't belong to
  - granting a role whose permissions exceed the granter's own
  - mutating/deleting system roles or roles still in use
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.seed_rbac import seed_org_rbac
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token(user_id: UUID | str) -> str:
    return create_access_token(
        data={"sub": str(user_id), "type": "access"},
        expires_delta=timedelta(minutes=15),
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


async def _create_org(client, token: str, *, name: str = "Acme Inc", slug: str) -> dict:
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": name, "slug": slug},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _add_member(
    client, token: str, org_id: str, user_id: str, *, role_slug: str | None = None
):
    payload: dict = {"user_id": user_id}
    if role_slug is not None:
        payload["role_slug"] = role_slug
    resp = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json=payload,
        headers=_auth(token),
    )
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _seed_rbac(db_session):
    """Idempotent: mirrors the seeding the real app performs at startup."""
    await seed_org_rbac(db_session)


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
    token = _token(owner["id"])
    return await _create_org(client, token, slug="acme")


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


class TestCreateOrganization:
    @pytest.mark.anyio
    async def test_creator_becomes_owner(self, client, owner) -> None:
        token = _token(owner["id"])
        org = await _create_org(client, token, slug="acme-create")

        assert org["owner_id"] == owner["id"]
        roles_by_user = {m["user"]["id"]: m["role"]["slug"] for m in org["members"]}
        assert roles_by_user[owner["id"]] == "org_owner"

    @pytest.mark.anyio
    async def test_duplicate_slug_returns_409(self, client, owner) -> None:
        token = _token(owner["id"])
        await _create_org(client, token, slug="dup-slug")
        resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Other", "slug": "dup-slug"},
            headers=_auth(token),
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_unauthenticated_cannot_create(self, client) -> None:
        resp = await client.post(
            "/api/v1/organizations", json={"name": "X", "slug": "no-auth"}
        )
        assert resp.status_code == 401


class TestGetOrganization:
    @pytest.mark.anyio
    async def test_member_can_get(self, client, organization, owner) -> None:
        token = _token(owner["id"])
        resp = await client.get(
            f"/api/v1/organizations/{organization['id']}", headers=_auth(token)
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_outsider_cannot_get_org_they_dont_belong_to(
        self, client, organization, outsider
    ) -> None:
        token = _token(outsider["id"])
        resp = await client.get(
            f"/api/v1/organizations/{organization['id']}", headers=_auth(token)
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_unknown_organization_returns_404(self, client, owner) -> None:
        token = _token(owner["id"])
        resp = await client.get(
            f"/api/v1/organizations/{uuid4()}", headers=_auth(token)
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_superuser_can_get_any_organization(
        self, client, organization, db_session
    ) -> None:
        su = await _register(client, "super1@test.com")
        await _make_superuser(db_session, su["id"])
        token = _token(su["id"])
        resp = await client.get(
            f"/api/v1/organizations/{organization['id']}", headers=_auth(token)
        )
        assert resp.status_code == 200


class TestUpdateOrganization:
    @pytest.mark.anyio
    async def test_owner_can_update(self, client, organization, owner) -> None:
        token = _token(owner["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}",
            json={"name": "Renamed Inc"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Inc"

    @pytest.mark.anyio
    async def test_outsider_cannot_update_org_they_dont_belong_to(
        self, client, organization, outsider
    ) -> None:
        token = _token(outsider["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}",
            json={"name": "Hacked"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_plain_member_without_permission_cannot_update(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await _add_member(client, owner_token, organization["id"], member["id"])
        assert resp.status_code == 201, resp.text

        member_token = _token(member["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}",
            json={"name": "Nope"},
            headers=_auth(member_token),
        )
        assert resp.status_code == 403


class TestDeleteOrganization:
    @pytest.mark.anyio
    async def test_owner_can_delete(self, client, organization, owner) -> None:
        token = _token(owner["id"])
        resp = await client.delete(
            f"/api/v1/organizations/{organization['id']}", headers=_auth(token)
        )
        assert resp.status_code == 204

        resp = await client.get(
            f"/api/v1/organizations/{organization['id']}", headers=_auth(token)
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_admin_role_cannot_delete_organization(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await _add_member(
            client,
            owner_token,
            organization["id"],
            member["id"],
            role_slug="org_admin",
        )
        assert resp.status_code == 201, resp.text

        member_token = _token(member["id"])
        resp = await client.delete(
            f"/api/v1/organizations/{organization['id']}", headers=_auth(member_token)
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------


class TestMembership:
    @pytest.mark.anyio
    async def test_owner_can_add_member_with_default_role(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await _add_member(client, owner_token, organization["id"], member["id"])
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"]["slug"] == "org_member"

    @pytest.mark.anyio
    async def test_add_existing_member_returns_409(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(client, owner_token, organization["id"], member["id"])
        resp = await _add_member(client, owner_token, organization["id"], member["id"])
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_add_unknown_user_returns_404(
        self, client, organization, owner
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await _add_member(client, owner_token, organization["id"], str(uuid4()))
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_outsider_cannot_add_member_to_org_they_dont_belong_to(
        self, client, organization, outsider, member
    ) -> None:
        outsider_token = _token(outsider["id"])
        resp = await _add_member(
            client, outsider_token, organization["id"], member["id"]
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_member_can_remove_self(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(client, owner_token, organization["id"], member["id"])

        member_token = _token(member["id"])
        resp = await client.delete(
            f"/api/v1/organizations/{organization['id']}/members/{member['id']}",
            headers=_auth(member_token),
        )
        assert resp.status_code == 204

    @pytest.mark.anyio
    async def test_plain_member_cannot_remove_others(
        self, client, organization, owner, member, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(client, owner_token, organization["id"], member["id"])
        await _add_member(client, owner_token, organization["id"], outsider["id"])

        member_token = _token(member["id"])
        resp = await client.delete(
            f"/api/v1/organizations/{organization['id']}/members/{outsider['id']}",
            headers=_auth(member_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_cannot_remove_last_owner(self, client, organization, owner) -> None:
        owner_token = _token(owner["id"])
        resp = await client.delete(
            f"/api/v1/organizations/{organization['id']}/members/{owner['id']}",
            headers=_auth(owner_token),
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_cannot_demote_last_owner(self, client, organization, owner) -> None:
        owner_token = _token(owner["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}/members/{owner['id']}",
            json={"role_slug": "org_member"},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Dynamic role-grant guard — cannot grant permissions you don't hold
# ---------------------------------------------------------------------------


class TestRoleAssignmentGuard:
    @pytest.mark.anyio
    async def test_admin_can_grant_admin_role(
        self, client, organization, owner, member, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(
            client, owner_token, organization["id"], member["id"], role_slug="org_admin"
        )
        await _add_member(client, owner_token, organization["id"], outsider["id"])

        admin_token = _token(member["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}/members/{outsider['id']}",
            json={"role_slug": "org_admin"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"]["slug"] == "org_admin"

    @pytest.mark.anyio
    async def test_admin_cannot_grant_owner_role_exceeding_their_permissions(
        self, client, organization, owner, member, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(
            client, owner_token, organization["id"], member["id"], role_slug="org_admin"
        )
        await _add_member(client, owner_token, organization["id"], outsider["id"])

        admin_token = _token(member["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}/members/{outsider['id']}",
            json={"role_slug": "org_owner"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_plain_member_cannot_assign_any_role(
        self, client, organization, owner, member, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(client, owner_token, organization["id"], member["id"])
        await _add_member(client, owner_token, organization["id"], outsider["id"])

        member_token = _token(member["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}/members/{outsider['id']}",
            json={"role_slug": "org_admin"},
            headers=_auth(member_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_custom_role_exceeding_admin_permissions_cannot_be_granted(
        self, client, organization, owner, member, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        # Owner defines a custom role carrying a permission ("delete") that
        # an org_admin does not hold.
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Billing Admin",
                "slug": "billing-admin",
                "organization_id": organization["id"],
                "permission_slugs": ["organizations:delete"],
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 201, resp.text
        custom_role = resp.json()

        await _add_member(
            client, owner_token, organization["id"], member["id"], role_slug="org_admin"
        )
        await _add_member(client, owner_token, organization["id"], outsider["id"])

        admin_token = _token(member["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}/members/{outsider['id']}",
            json={"role_id": custom_role["id"]},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_owner_can_grant_custom_role(
        self, client, organization, owner, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Billing Admin",
                "slug": "billing-admin-2",
                "organization_id": organization["id"],
                "permission_slugs": ["organizations:delete"],
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 201, resp.text
        custom_role = resp.json()

        await _add_member(client, owner_token, organization["id"], outsider["id"])
        resp = await client.patch(
            f"/api/v1/organizations/{organization['id']}/members/{outsider['id']}",
            json={"role_id": custom_role["id"]},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"]["slug"] == "billing-admin-2"


# ---------------------------------------------------------------------------
# Role management (CRUD) — section 5
# ---------------------------------------------------------------------------


class TestRoleManagement:
    @pytest.mark.anyio
    async def test_superuser_can_create_global_role(
        self, client, owner, db_session
    ) -> None:
        await _make_superuser(db_session, owner["id"])
        token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={"name": "Auditor Plus", "slug": "auditor-plus"},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["organization_id"] is None

    @pytest.mark.anyio
    async def test_non_superuser_cannot_create_global_role(self, client, owner) -> None:
        token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={"name": "Sneaky Global", "slug": "sneaky-global"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_org_member_cannot_create_custom_role(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        await _add_member(client, owner_token, organization["id"], member["id"])

        member_token = _token(member["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "Shadow Role",
                "slug": "shadow-role",
                "organization_id": organization["id"],
            },
            headers=_auth(member_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_duplicate_slug_in_same_org_scope_returns_409(
        self, client, organization, owner
    ) -> None:
        owner_token = _token(owner["id"])
        payload = {
            "name": "Reviewer",
            "slug": "reviewer",
            "organization_id": organization["id"],
        }
        resp1 = await client.post(
            "/api/v1/roles", json=payload, headers=_auth(owner_token)
        )
        assert resp1.status_code == 201, resp1.text
        resp2 = await client.post(
            "/api/v1/roles", json=payload, headers=_auth(owner_token)
        )
        assert resp2.status_code == 409

    @pytest.mark.anyio
    async def test_two_organizations_can_reuse_the_same_custom_role_slug(
        self, client, organization, owner
    ) -> None:
        owner_token = _token(owner["id"])
        other_owner = await _register(client, "other-owner@test.com")
        other_org = await _create_org(client, _token(other_owner["id"]), slug="globex")

        resp1 = await client.post(
            "/api/v1/roles",
            json={
                "name": "Manager",
                "slug": "manager",
                "organization_id": organization["id"],
            },
            headers=_auth(owner_token),
        )
        assert resp1.status_code == 201, resp1.text

        resp2 = await client.post(
            "/api/v1/roles",
            json={
                "name": "Manager",
                "slug": "manager",
                "organization_id": other_org["id"],
            },
            headers=_auth(_token(other_owner["id"])),
        )
        assert resp2.status_code == 201, resp2.text

    @pytest.mark.anyio
    async def test_cannot_delete_system_role(self, client, owner, db_session) -> None:
        await _make_superuser(db_session, owner["id"])
        token = _token(owner["id"])

        resp = await client.get("/api/v1/roles", headers=_auth(token))
        assert resp.status_code == 200
        org_owner_role = next(r for r in resp.json() if r["slug"] == "org_owner")

        resp = await client.delete(
            f"/api/v1/roles/{org_owner_role['id']}", headers=_auth(token)
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_cannot_delete_role_currently_assigned_to_a_member(
        self, client, organization, owner, member
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await client.post(
            "/api/v1/roles",
            json={
                "name": "In Use Role",
                "slug": "in-use-role",
                "organization_id": organization["id"],
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 201, resp.text
        role = resp.json()

        resp = await _add_member(
            client,
            owner_token,
            organization["id"],
            member["id"],
            role_slug="in-use-role",
        )
        assert resp.status_code == 201, resp.text

        resp = await client.delete(
            f"/api/v1/roles/{role['id']}", headers=_auth(owner_token)
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Listing — N+1 sanity (just behavioural correctness; eager loading is
# enforced declaratively on the models, see app/models/organization*.py)
# ---------------------------------------------------------------------------


class TestListOrganizations:
    @pytest.mark.anyio
    async def test_caller_only_sees_their_own_organizations(
        self, client, organization, owner, outsider
    ) -> None:
        owner_token = _token(owner["id"])
        resp = await client.get("/api/v1/organizations", headers=_auth(owner_token))
        assert resp.status_code == 200
        assert any(o["id"] == organization["id"] for o in resp.json()["items"])

        outsider_token = _token(outsider["id"])
        resp = await client.get("/api/v1/organizations", headers=_auth(outsider_token))
        assert resp.status_code == 200
        assert all(o["id"] != organization["id"] for o in resp.json()["items"])
