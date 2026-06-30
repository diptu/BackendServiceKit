"""Integration tests — ResourceClaimService against real in-memory SQLite."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ResourceClaimConflictError, ResourceClaimNotFoundError
from app.services.resource_claim_service import ResourceClaimService


@pytest.fixture
def svc(session: AsyncSession) -> ResourceClaimService:
    return ResourceClaimService(session)


async def test_claim_resource(svc: ResourceClaimService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    claim = await svc.claim(tid, rid, "document", "test-service")
    assert claim.tenant_id == tid
    assert claim.resource_id == rid
    assert claim.resource_type == "document"
    assert claim.source_service == "test-service"


async def test_claim_same_tenant_idempotent(svc: ResourceClaimService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    claim1 = await svc.claim(tid, rid, "document", "test-service")
    claim2 = await svc.claim(tid, rid, "document", "test-service")
    assert claim1.id == claim2.id


async def test_claim_conflict_different_tenant(svc: ResourceClaimService) -> None:
    tid1 = uuid4()
    tid2 = uuid4()
    rid = str(uuid4())
    await svc.claim(tid1, rid, "document", "test-service")
    with pytest.raises(ResourceClaimConflictError):
        await svc.claim(tid2, rid, "document", "test-service")


async def test_release_claim(svc: ResourceClaimService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    await svc.claim(tid, rid, "document", "test-service")
    await svc.release(tid, rid, "document")
    with pytest.raises(ResourceClaimNotFoundError):
        await svc.get_owner(rid, "document")


async def test_get_owner_unclaimed(svc: ResourceClaimService) -> None:
    rid = str(uuid4())
    with pytest.raises(ResourceClaimNotFoundError):
        await svc.get_owner(rid, "document")


async def test_get_owner_found(svc: ResourceClaimService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    await svc.claim(tid, rid, "workspace", "test-service")
    owner_claim = await svc.get_owner(rid, "workspace")
    assert owner_claim.tenant_id == tid


async def test_bulk_claim(svc: ResourceClaimService) -> None:
    tid = uuid4()
    from app.schemas.isolation import ClaimItem
    items = [
        ClaimItem(resource_id=str(uuid4()), resource_type="document"),
        ClaimItem(resource_id=str(uuid4()), resource_type="workspace"),
        ClaimItem(resource_id=str(uuid4()), resource_type="user"),
    ]
    results = await svc.bulk_claim(tid, items, "bulk-service")
    assert len(results) == 3
    for r in results:
        assert r.tenant_id == tid


async def test_release_nonexistent_is_noop(svc: ResourceClaimService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    await svc.release(tid, rid, "document")


async def test_claim_multiple_resource_types(svc: ResourceClaimService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    claim1 = await svc.claim(tid, rid, "document", "svc1")
    claim2 = await svc.claim(tid, rid, "workspace", "svc1")
    assert claim1.id != claim2.id
    assert claim1.resource_type == "document"
    assert claim2.resource_type == "workspace"
