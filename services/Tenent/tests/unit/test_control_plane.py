"""Control Plane registry: register/resolve/get/dsn/deprovision, subdomain
uniqueness, credential assembly (no raw secret stored), and the end-to-end
loop where the shared ControlPlaneConnectionResolver reads a tenant's DSN back
out of Tenent.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from shared.db.resolver import (
    ControlPlaneConnectionResolver,
    ControlPlaneUnavailableError,
)

_CP = "/api/v1/control-plane"


def _payload(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "subdomain": "acme",
        "db_host": "db.internal",
        "db_name": "tenant_acme",
        "db_user": "acme_app",
    }
    base.update(over)
    return base


async def _register(
    client: AsyncClient, tenant_id: uuid.UUID, **over: object
) -> dict[str, object]:
    r = await client.post(f"{_CP}/connections/{tenant_id}", json=_payload(**over))
    assert r.status_code == 201, r.text
    body: dict[str, object] = r.json()
    return body


@pytest.mark.asyncio
async def test_register_then_get_connection(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await _register(client, tenant_id, subdomain=f"acme-{tenant_id.hex[:6]}")

    r = await client.get(f"{_CP}/connections/{tenant_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tenant_id)
    assert body["db_host"] == "db.internal"
    assert body["status"] == "provisioning"
    # Never a password field — none is stored.
    assert "password" not in body


@pytest.mark.asyncio
async def test_resolve_subdomain(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    sub = f"resolve-{tenant_id.hex[:6]}"
    await _register(client, tenant_id, subdomain=sub)

    r = await client.get(f"{_CP}/resolve", params={"subdomain": sub})
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tenant_id)
    assert body["subdomain"] == sub
    # No connection coordinates or credentials leak to the resolver caller.
    assert set(body.keys()) == {"tenant_id", "subdomain", "status"}


@pytest.mark.asyncio
async def test_resolve_unknown_subdomain_404(client: AsyncClient) -> None:
    r = await client.get(f"{_CP}/resolve", params={"subdomain": "nobody-here"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_subdomain_conflict_across_tenants(client: AsyncClient) -> None:
    sub = f"shared-{uuid.uuid4().hex[:6]}"
    await _register(client, uuid.uuid4(), subdomain=sub)

    r = await client.post(
        f"{_CP}/connections/{uuid.uuid4()}", json=_payload(subdomain=sub)
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_reregister_same_tenant_is_idempotent_update(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    sub = f"idem-{tenant_id.hex[:6]}"
    await _register(client, tenant_id, subdomain=sub, db_host="old.host")
    await _register(client, tenant_id, subdomain=sub, db_host="new.host")

    r = await client.get(f"{_CP}/connections/{tenant_id}")
    assert r.json()["db_host"] == "new.host"


@pytest.mark.asyncio
async def test_dsn_without_secret_has_no_password(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await _register(client, tenant_id, subdomain=f"nopw-{tenant_id.hex[:6]}")

    r = await client.get(f"{_CP}/connections/{tenant_id}/dsn")
    assert r.status_code == 200
    dsn = r.json()["dsn"]
    assert dsn == "postgresql+asyncpg://acme_app@db.internal:5432/tenant_acme"


@pytest.mark.asyncio
async def test_dsn_with_secret_is_assembled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id = uuid.uuid4()
    monkeypatch.setenv("TENANT_DB_SECRET_TENANT_ACME", "s3cr3t/pw")
    await _register(
        client,
        tenant_id,
        subdomain=f"pw-{tenant_id.hex[:6]}",
        secret_ref="tenant-acme",
    )

    r = await client.get(f"{_CP}/connections/{tenant_id}/dsn")
    assert r.status_code == 200
    dsn = r.json()["dsn"]
    # Password is URL-encoded into the userinfo.
    assert dsn == (
        "postgresql+asyncpg://acme_app:s3cr3t%2Fpw@db.internal:5432/tenant_acme"
    )


@pytest.mark.asyncio
async def test_dsn_missing_secret_fails_closed_503(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    await _register(
        client,
        tenant_id,
        subdomain=f"missing-{tenant_id.hex[:6]}",
        secret_ref="not-in-env",
    )
    r = await client.get(f"{_CP}/connections/{tenant_id}/dsn")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_deprovision_disables_connection(client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    sub = f"gone-{tenant_id.hex[:6]}"
    await _register(client, tenant_id, subdomain=sub)

    r = await client.delete(f"{_CP}/connections/{tenant_id}")
    assert r.status_code == 204

    r = await client.get(f"{_CP}/resolve", params={"subdomain": sub})
    assert r.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_get_unknown_connection_404(client: AsyncClient) -> None:
    r = await client.get(f"{_CP}/connections/{uuid.uuid4()}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# End-to-end: the shared resolver reads a DSN back out of Tenent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shared_resolver_reads_dsn_from_control_plane(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id = uuid.uuid4()
    monkeypatch.setenv("TENANT_DB_SECRET_TENANT_ACME", "pw")
    await _register(
        client,
        tenant_id,
        subdomain=f"e2e-{tenant_id.hex[:6]}",
        secret_ref="tenant-acme",
    )

    # Point the production-style resolver straight at Tenent's ASGI app.
    resolver = ControlPlaneConnectionResolver("http://test", http_client=client)
    dsn = await resolver.resolve(tenant_id)
    assert dsn == "postgresql+asyncpg://acme_app:pw@db.internal:5432/tenant_acme"


@pytest.mark.asyncio
async def test_shared_resolver_unknown_tenant_fails_closed(
    client: AsyncClient,
) -> None:
    resolver = ControlPlaneConnectionResolver("http://test", http_client=client)
    with pytest.raises(ControlPlaneUnavailableError):
        await resolver.resolve(uuid.uuid4())
