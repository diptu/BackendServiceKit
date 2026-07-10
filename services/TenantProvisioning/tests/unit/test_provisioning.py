"""Provisioning workflow: create → migrate → register, idempotency, retry,
deprovision, and failure recording — exercised end-to-end against real SQLite
tenant databases (local backend, null Control Plane registrar).
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_provisioning_service
from app.core.config import settings
from app.infrastructure.control_plane import NullControlPlaneRegistrar
from app.infrastructure.database.dependencies import get_db
from app.infrastructure.provisioner import DatabaseProvisioner, ProvisionedDatabase
from app.main import app
from app.services.migration_runner import MarkerMigrationRunner
from app.services.provisioning_service import ProvisioningService

_CP = "/api/v1/provisioning/tenants"


@pytest.fixture
def tenant_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "local_provisioner_dir", str(tmp_path))
    monkeypatch.setattr(settings, "provisioner_backend", "local")
    monkeypatch.setattr(settings, "control_plane_register_enabled", False)
    return tmp_path


def _marker_services(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT service FROM provisioning_marker").fetchall()
        return sorted(r[0] for r in rows)
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_full_workflow_creates_and_migrates_tenant_db(
    client: AsyncClient, tenant_dir: Path
) -> None:
    tenant_id = uuid.uuid4()
    r = await client.post(_CP, json={"tenant_id": str(tenant_id), "subdomain": "acme"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["current_step"] == "done"
    assert body["db_name"] == f"tenant_{tenant_id.hex}.db"
    assert body["attempts"] == 1

    # The tenant's own database physically exists and was migrated.
    db_file = tenant_dir / f"tenant_{tenant_id.hex}.db"
    assert db_file.exists()
    assert _marker_services(db_file) == sorted(settings.managed_services)


@pytest.mark.asyncio
async def test_provision_is_idempotent(client: AsyncClient, tenant_dir: Path) -> None:
    tenant_id = uuid.uuid4()
    payload = {"tenant_id": str(tenant_id), "subdomain": "idem"}
    r1 = await client.post(_CP, json=payload)
    assert r1.json()["status"] == "completed"
    r2 = await client.post(_CP, json=payload)
    assert r2.json()["status"] == "completed"
    # Already-completed tenant is not re-provisioned — attempts stays at 1.
    assert r2.json()["attempts"] == 1


@pytest.mark.asyncio
async def test_get_and_list(client: AsyncClient, tenant_dir: Path) -> None:
    tenant_id = uuid.uuid4()
    await client.post(_CP, json={"tenant_id": str(tenant_id), "subdomain": "g"})

    r = await client.get(f"{_CP}/{tenant_id}")
    assert r.status_code == 200
    assert r.json()["tenant_id"] == str(tenant_id)

    r = await client.get(_CP, params={"status": "completed"})
    assert r.status_code == 200
    assert any(j["tenant_id"] == str(tenant_id) for j in r.json()["items"])


@pytest.mark.asyncio
async def test_get_unknown_404(client: AsyncClient, tenant_dir: Path) -> None:
    r = await client.get(f"{_CP}/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_deprovision_drops_the_tenant_db(
    client: AsyncClient, tenant_dir: Path
) -> None:
    tenant_id = uuid.uuid4()
    await client.post(_CP, json={"tenant_id": str(tenant_id), "subdomain": "gone"})
    db_file = tenant_dir / f"tenant_{tenant_id.hex}.db"
    assert db_file.exists()

    r = await client.delete(f"{_CP}/{tenant_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "deprovisioned"
    assert not db_file.exists()


@pytest.mark.asyncio
async def test_retry_on_completed_is_noop(
    client: AsyncClient, tenant_dir: Path
) -> None:
    tenant_id = uuid.uuid4()
    await client.post(_CP, json={"tenant_id": str(tenant_id), "subdomain": "r"})
    r = await client.post(f"{_CP}/{tenant_id}/retry")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


class _FailingProvisioner(DatabaseProvisioner):
    async def create(self, tenant_id: uuid.UUID) -> ProvisionedDatabase:
        raise RuntimeError("disk full")

    async def drop(self, tenant_id: uuid.UUID) -> None:
        return None


@pytest_asyncio.fixture
async def failing_client(
    db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    from httpx import ASGITransport

    async def _svc(db: AsyncSession = Depends(get_db)) -> ProvisioningService:
        return ProvisioningService(
            db,
            _FailingProvisioner(),
            MarkerMigrationRunner(),
            NullControlPlaneRegistrar(),
        )

    async def _get_db_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_provisioning_service] = _svc
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_failure_is_recorded_on_the_job(failing_client: AsyncClient) -> None:
    tenant_id = uuid.uuid4()
    r = await failing_client.post(
        _CP, json={"tenant_id": str(tenant_id), "subdomain": "boom"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "failed"
    assert body["current_step"] == "create_database"
    assert "disk full" in body["error"]
