"""Unit tests for TenantService using an in-memory SQLite database."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.enums import TenantStatus
from app.domain.exceptions import (
    InvalidTenantTransitionError,
    TenantLockedError,
    TenantNameConflictError,
    TenantNotFoundError,
)
from app.domain.commands import CreateTenantCmd, UpdateTenantCmd
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import Tenant  # noqa: F401
from app.infrastructure.database.models import TenantContact  # noqa: F401
from app.infrastructure.database.models import TenantMetadata  # noqa: F401
from app.infrastructure.database.models import TenantSettings  # noqa: F401
from app.infrastructure.repositories.tenant_contact import TenantContactRepository
from app.infrastructure.repositories.tenant_settings import TenantSettingsRepository
from app.services.tenant_service import TenantService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False)

_OWNER_ID = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with _SESSION_FACTORY() as s:
        yield s


@pytest.fixture
async def svc(session: AsyncSession) -> TenantService:
    return TenantService(session)


def _create_req(**overrides: object) -> CreateTenantCmd:
    data: dict[str, object] = {
        "name": "acme-corp",
        "display_name": "Acme Corporation",
        "owner_id": _OWNER_ID,
        "region": "us-east-1",
        "timezone": "UTC",
        "locale": "en-US",
        "currency": "USD",
    }
    data.update(overrides)
    return CreateTenantCmd(**data)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_tenant(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    assert tenant.name == "acme-corp"
    assert tenant.status == TenantStatus.DRAFT
    assert tenant.id is not None


async def test_create_sets_owner(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    assert tenant.owner_id == _OWNER_ID


async def test_create_provisions_settings(
    svc: TenantService, session: AsyncSession
) -> None:
    req = _create_req(timezone="America/Chicago", locale="en-US", currency="EUR")
    tenant = await svc.create(req)
    settings = await TenantSettingsRepository(session).get_by_tenant_id(tenant.id)
    assert settings is not None
    assert settings.tenant_id == tenant.id
    assert settings.timezone == "America/Chicago"
    assert settings.locale == "en-US"
    assert settings.currency == "EUR"


async def test_create_provisions_owner_contact(
    svc: TenantService, session: AsyncSession
) -> None:
    tenant = await svc.create(_create_req())
    contacts = await TenantContactRepository(session).get_active_by_tenant(tenant.id)
    assert len(contacts) == 1
    assert contacts[0].user_id == _OWNER_ID
    assert contacts[0].role == "owner"


async def test_create_settings_defaults_language_theme(
    svc: TenantService, session: AsyncSession
) -> None:
    tenant = await svc.create(_create_req())
    settings = await TenantSettingsRepository(session).get_by_tenant_id(tenant.id)
    assert settings is not None
    assert settings.language == "en"
    assert settings.default_theme == "light"
    assert settings.session_timeout_minutes == 60


async def test_create_duplicate_name_raises(svc: TenantService) -> None:
    await svc.create(_create_req())
    with pytest.raises(TenantNameConflictError):
        await svc.create(_create_req())


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


async def test_get_returns_tenant(svc: TenantService) -> None:
    created = await svc.create(_create_req())
    fetched = await svc.get(created.id)
    assert fetched.id == created.id


async def test_get_missing_raises(svc: TenantService) -> None:
    with pytest.raises(TenantNotFoundError):
        await svc.get(uuid4())


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_empty(svc: TenantService) -> None:
    result = await svc.list()
    assert result.items == []
    assert result.total == 0
    assert result.has_more is False


async def test_list_returns_created(svc: TenantService) -> None:
    await svc.create(_create_req())
    result = await svc.list()
    assert result.total == 1
    assert len(result.items) == 1


async def test_list_filter_by_status(svc: TenantService) -> None:
    await svc.create(_create_req())
    result = await svc.list(status_filter="draft")
    assert result.total == 1
    result_active = await svc.list(status_filter="active")
    assert result_active.total == 0


async def test_list_filter_by_region(svc: TenantService) -> None:
    await svc.create(_create_req(name="acme-us", region="us-east-1"))
    await svc.create(_create_req(name="acme-eu", region="eu-west-1"))
    result = await svc.list(region="us-east-1")
    assert result.total == 1
    assert result.items[0].name == "acme-us"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_display_name(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    updated = await svc.update(tenant.id, UpdateTenantCmd(display_name="New Name"))
    assert updated.display_name == "New Name"


async def test_update_no_changes_is_noop(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    updated = await svc.update(tenant.id, UpdateTenantCmd())
    assert updated.display_name == tenant.display_name


async def test_update_archived_raises_locked(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    # Drive to archived via valid transitions
    tenant.status = TenantStatus.ACTIVE
    await svc._repo.save(tenant)
    await svc.archive(tenant.id)
    with pytest.raises(TenantLockedError):
        await svc.update(tenant.id, UpdateTenantCmd(display_name="Blocked"))


async def test_update_missing_raises(svc: TenantService) -> None:
    with pytest.raises(TenantNotFoundError):
        await svc.update(uuid4(), UpdateTenantCmd(display_name="X"))


# ---------------------------------------------------------------------------
# Soft-delete
# ---------------------------------------------------------------------------


async def test_delete_requires_archived(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    with pytest.raises(InvalidTenantTransitionError):
        await svc.delete(tenant.id)


async def test_delete_archived_tenant(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.ACTIVE
    await svc._repo.save(tenant)
    await svc.archive(tenant.id)
    await svc.delete(tenant.id)
    # Should no longer be visible in a normal get
    with pytest.raises(TenantNotFoundError):
        await svc.get(tenant.id)


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


async def test_pend_from_provisioning(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.PROVISIONING
    await svc._repo.save(tenant)
    result = await svc.pend(tenant.id)
    assert result.status == TenantStatus.PENDING


async def test_activate_from_provisioning_raises(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.PROVISIONING
    await svc._repo.save(tenant)
    with pytest.raises(InvalidTenantTransitionError):
        await svc.activate(tenant.id)


async def test_activate_from_pending(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.PENDING
    await svc._repo.save(tenant)
    result = await svc.activate(tenant.id)
    assert result.status == TenantStatus.ACTIVE


async def test_activate_from_suspended(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.SUSPENDED
    await svc._repo.save(tenant)
    result = await svc.activate(tenant.id)
    assert result.status == TenantStatus.ACTIVE


async def test_activate_from_draft_raises(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    with pytest.raises(InvalidTenantTransitionError):
        await svc.activate(tenant.id)


async def test_suspend_from_active(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.ACTIVE
    await svc._repo.save(tenant)
    result = await svc.suspend(tenant.id, reason="overdue")
    assert result.status == TenantStatus.SUSPENDED


async def test_suspend_from_draft_raises(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    with pytest.raises(InvalidTenantTransitionError):
        await svc.suspend(tenant.id)


async def test_archive_from_active(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.ACTIVE
    await svc._repo.save(tenant)
    result = await svc.archive(tenant.id)
    assert result.status == TenantStatus.ARCHIVED


async def test_archive_from_suspended(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    tenant.status = TenantStatus.SUSPENDED
    await svc._repo.save(tenant)
    result = await svc.archive(tenant.id)
    assert result.status == TenantStatus.ARCHIVED


async def test_archive_from_draft_raises(svc: TenantService) -> None:
    tenant = await svc.create(_create_req())
    with pytest.raises(InvalidTenantTransitionError):
        await svc.archive(tenant.id)


async def test_transition_missing_raises(svc: TenantService) -> None:
    with pytest.raises(TenantNotFoundError):
        await svc.activate(uuid4())
