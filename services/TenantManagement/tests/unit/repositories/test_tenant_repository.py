"""Unit tests for TenantRepository using an in-memory SQLite database."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.enums import TenantStatus
from app.infrastructure.database.base import Base
from app.models import Tenant, TenantSettings, TenantMetadata, TenantContact  # noqa: F401
from app.repositories.base import decode_cursor, encode_cursor
from app.repositories.tenant import TenantFilter, TenantRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
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
async def repo(session: AsyncSession) -> TenantRepository:
    return TenantRepository(session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_tenant(
    *,
    name: str = "test-corp",
    display_name: str = "Test Corp",
    status: str = TenantStatus.ACTIVE,
    region: str = "us-east-1",
) -> Tenant:
    now = datetime.now(timezone.utc)
    return Tenant(
        id=uuid4(),
        name=name,
        display_name=display_name,
        status=status,
        region=region,
        timezone="UTC",
        locale="en-US",
        currency="USD",
        owner_id=uuid4(),
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_and_get_by_id(repo: TenantRepository) -> None:
    tenant = make_tenant()
    created = await repo.create(tenant)

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "test-corp"


async def test_get_by_id_missing(repo: TenantRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# get_by_name / exists
# ---------------------------------------------------------------------------


async def test_get_by_name(repo: TenantRepository) -> None:
    tenant = make_tenant(name="alpha-corp")
    await repo.create(tenant)

    found = await repo.get_by_name("alpha-corp")
    assert found is not None
    assert found.name == "alpha-corp"


async def test_get_by_name_missing(repo: TenantRepository) -> None:
    assert await repo.get_by_name("ghost") is None


async def test_exists_by_name_true(repo: TenantRepository) -> None:
    await repo.create(make_tenant(name="acme"))
    assert await repo.exists_by_name("acme") is True


async def test_exists_by_name_false(repo: TenantRepository) -> None:
    assert await repo.exists_by_name("nope") is False


async def test_exists_by_id_true(repo: TenantRepository) -> None:
    t = await repo.create(make_tenant())
    assert await repo.exists_by_id(t.id) is True


async def test_exists_by_id_false(repo: TenantRepository) -> None:
    assert await repo.exists_by_id(uuid4()) is False


# ---------------------------------------------------------------------------
# save (update)
# ---------------------------------------------------------------------------


async def test_save_updates_field(repo: TenantRepository) -> None:
    tenant = await repo.create(make_tenant())
    tenant.display_name = "Updated Name"
    saved = await repo.save(tenant)
    assert saved.display_name == "Updated Name"

    refetched = await repo.get_by_id(tenant.id)
    assert refetched is not None
    assert refetched.display_name == "Updated Name"


# ---------------------------------------------------------------------------
# soft_delete / restore
# ---------------------------------------------------------------------------


async def test_soft_delete(repo: TenantRepository) -> None:
    tenant = await repo.create(make_tenant())
    await repo.soft_delete(tenant)

    # Default get excludes deleted
    assert await repo.get_by_id(tenant.id) is None

    # include_deleted=True returns it
    found = await repo.get_by_id(tenant.id, include_deleted=True)
    assert found is not None
    assert found.deleted_at is not None
    assert found.status == TenantStatus.DELETED


async def test_restore(repo: TenantRepository) -> None:
    tenant = await repo.create(make_tenant())
    await repo.soft_delete(tenant)

    tenant.status = TenantStatus.ARCHIVED
    restored = await repo.restore(tenant)
    assert restored.deleted_at is None

    found = await repo.get_by_id(restored.id)
    assert found is not None


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


async def test_count_empty(repo: TenantRepository) -> None:
    assert await repo.count() == 0


async def test_count_with_records(repo: TenantRepository) -> None:
    await repo.create(make_tenant(name="t1", status=TenantStatus.ACTIVE))
    await repo.create(make_tenant(name="t2", status=TenantStatus.SUSPENDED))
    assert await repo.count() == 2


async def test_count_with_status_filter(repo: TenantRepository) -> None:
    await repo.create(make_tenant(name="a1", status=TenantStatus.ACTIVE))
    await repo.create(make_tenant(name="s1", status=TenantStatus.SUSPENDED))
    f = TenantFilter(status=TenantStatus.ACTIVE)
    assert await repo.count(f) == 1


async def test_count_excludes_deleted(repo: TenantRepository) -> None:
    t = await repo.create(make_tenant())
    await repo.soft_delete(t)
    assert await repo.count() == 0


# ---------------------------------------------------------------------------
# list (pagination)
# ---------------------------------------------------------------------------


async def test_list_empty(repo: TenantRepository) -> None:
    page = await repo.list()
    assert page.items == []
    assert page.total == 0
    assert page.has_more is False
    assert page.next_cursor is None


async def test_list_single_page(repo: TenantRepository) -> None:
    for i in range(3):
        await repo.create(make_tenant(name=f"corp-{i}"))

    page = await repo.list(limit=10)
    assert len(page.items) == 3
    assert page.total == 3
    assert page.has_more is False
    assert page.next_cursor is None


async def test_list_pagination_cursor(repo: TenantRepository) -> None:
    for i in range(5):
        await repo.create(make_tenant(name=f"p-{i:02d}"))

    page1 = await repo.list(limit=3)
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert page1.next_cursor is not None

    page2 = await repo.list(limit=3, cursor=page1.next_cursor)
    assert len(page2.items) == 2
    assert page2.has_more is False
    assert page2.next_cursor is None

    # No overlapping items
    ids1 = {t.id for t in page1.items}
    ids2 = {t.id for t in page2.items}
    assert ids1.isdisjoint(ids2)


async def test_list_filter_by_region(repo: TenantRepository) -> None:
    await repo.create(make_tenant(name="us-corp", region="us-east-1"))
    await repo.create(make_tenant(name="eu-corp", region="eu-west-1"))

    page = await repo.list(filters=TenantFilter(region="us-east-1"))
    assert len(page.items) == 1
    assert page.items[0].name == "us-corp"


async def test_list_filter_by_status(repo: TenantRepository) -> None:
    await repo.create(make_tenant(name="act", status=TenantStatus.ACTIVE))
    await repo.create(make_tenant(name="sus", status=TenantStatus.SUSPENDED))

    page = await repo.list(filters=TenantFilter(status=TenantStatus.SUSPENDED))
    assert len(page.items) == 1
    assert page.items[0].name == "sus"


async def test_list_search(repo: TenantRepository) -> None:
    await repo.create(make_tenant(name="apple-inc", display_name="Apple Inc"))
    await repo.create(make_tenant(name="meta-corp", display_name="Meta Corporation"))

    page = await repo.list(filters=TenantFilter(search="apple"))
    assert len(page.items) == 1
    assert page.items[0].name == "apple-inc"


# ---------------------------------------------------------------------------
# Cursor encode / decode round-trip
# ---------------------------------------------------------------------------


def test_cursor_round_trip() -> None:
    now = datetime.now(timezone.utc)
    uid = uuid4()
    cursor = encode_cursor(now, uid)
    decoded_dt, decoded_id = decode_cursor(cursor)
    # datetime round-trips through ISO format
    assert decoded_dt.isoformat() == now.isoformat()
    assert decoded_id == uid


def test_cursor_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Invalid pagination cursor"):
        decode_cursor("not-a-valid-cursor!!!")
