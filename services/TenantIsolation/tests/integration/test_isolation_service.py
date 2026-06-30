"""Integration tests — IsolationService against real in-memory SQLite."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IsolationDecision, PolicyType
from app.domain.exceptions import (
    InvalidQueryFilterError,
    IsolationValidationError,
    IsolationViolationError,
)
from app.models.isolation_policy import IsolationPolicy
from app.repositories.base import PageResult
from app.services.isolation_service import IsolationService


@pytest.fixture
def svc(session: AsyncSession) -> IsolationService:
    return IsolationService(session)


async def _create_policy(
    session: AsyncSession,
    tenant_id: object,
    *,
    policy_type: str = "strict",
    allowed_partner_ids: list[str] | None = None,
) -> IsolationPolicy:
    from uuid import uuid4 as _uuid4
    policy = IsolationPolicy(
        id=_uuid4(),
        tenant_id=tenant_id,  # type: ignore[arg-type]
        name="test-policy",
        policy_type=policy_type,
        allow_cross_tenant_read=policy_type == "partner",
        allowed_partner_tenant_ids=allowed_partner_ids or [],
        is_active=True,
    )
    session.add(policy)
    await session.flush()
    return policy


# ── validate ──────────────────────────────────────────────────────────────────

async def test_validate_all_owned(svc: IsolationService, session: AsyncSession) -> None:
    tid = uuid4()
    rid = str(uuid4())

    from app.models.resource_claim import ResourceClaim
    from datetime import datetime, timezone
    claim = ResourceClaim(id=uuid4(), tenant_id=tid, resource_id=rid, resource_type="document", source_service="test", claimed_at=datetime.now(timezone.utc))
    session.add(claim)
    await session.flush()

    resp = await svc.validate(tid, [rid], "document")
    assert resp.decision == IsolationDecision.ALLOW
    assert resp.violations == []


async def test_validate_some_unowned(svc: IsolationService, session: AsyncSession) -> None:
    tid = uuid4()
    other_tid = uuid4()
    rid1 = str(uuid4())
    rid2 = str(uuid4())

    from app.models.resource_claim import ResourceClaim
    from datetime import datetime, timezone
    claim = ResourceClaim(id=uuid4(), tenant_id=tid, resource_id=rid1, resource_type="document", source_service="test", claimed_at=datetime.now(timezone.utc))
    claim2 = ResourceClaim(id=uuid4(), tenant_id=other_tid, resource_id=rid2, resource_type="document", source_service="test", claimed_at=datetime.now(timezone.utc))
    session.add(claim)
    session.add(claim2)
    await session.flush()

    resp = await svc.validate(tid, [rid1, rid2], "document")
    assert resp.decision == IsolationDecision.DENY
    assert rid2 in resp.violations
    assert rid1 not in resp.violations


async def test_validate_empty_claims(svc: IsolationService) -> None:
    tid = uuid4()
    rid = str(uuid4())
    resp = await svc.validate(tid, [rid], "document")
    assert resp.decision == IsolationDecision.DENY
    assert rid in resp.violations


# ── check_access ──────────────────────────────────────────────────────────────

async def test_check_access_same_tenant(svc: IsolationService) -> None:
    tid = uuid4()
    resp = await svc.check_access(tid, tid, "res1", "document", "read")
    assert resp.decision == IsolationDecision.ALLOW
    assert "same-tenant" in (resp.reason or "")


async def test_check_access_cross_tenant_strict_policy(
    svc: IsolationService,
) -> None:
    caller = uuid4()
    target = uuid4()
    resp = await svc.check_access(caller, target, "res1", "document", "read")
    assert resp.decision == IsolationDecision.DENY
    assert "strict" in (resp.reason or "")


async def test_check_access_cross_tenant_partner_policy_read(
    svc: IsolationService, session: AsyncSession
) -> None:
    caller = uuid4()
    target = uuid4()
    await _create_policy(
        session,
        caller,
        policy_type="partner",
        allowed_partner_ids=[str(target)],
    )
    await session.commit()

    resp = await svc.check_access(caller, target, "res1", "document", "read")
    assert resp.decision == IsolationDecision.ALLOW


async def test_check_access_cross_tenant_partner_policy_write(
    svc: IsolationService, session: AsyncSession
) -> None:
    caller = uuid4()
    target = uuid4()
    await _create_policy(
        session,
        caller,
        policy_type="partner",
        allowed_partner_ids=[str(target)],
    )
    await session.commit()

    resp = await svc.check_access(caller, target, "res1", "document", "write")
    assert resp.decision == IsolationDecision.DENY
    assert "read only" in (resp.reason or "")


async def test_check_access_cross_tenant_internal_policy(
    svc: IsolationService, session: AsyncSession
) -> None:
    caller = uuid4()
    target = uuid4()
    await _create_policy(session, caller, policy_type="internal")
    await session.commit()

    resp = await svc.check_access(caller, target, "res1", "document", "admin")
    assert resp.decision == IsolationDecision.ALLOW


# ── validate_query ────────────────────────────────────────────────────────────

async def test_validate_query_valid(svc: IsolationService) -> None:
    tid = uuid4()
    resp = await svc.validate_query(tid, {"tenant_id": str(tid), "other": "val"})
    assert resp.is_valid is True


async def test_validate_query_missing_tenant(svc: IsolationService) -> None:
    tid = uuid4()
    with pytest.raises(InvalidQueryFilterError):
        await svc.validate_query(tid, {"other": "val"})


async def test_validate_query_wrong_tenant(svc: IsolationService) -> None:
    tid = uuid4()
    other = uuid4()
    with pytest.raises(IsolationViolationError):
        await svc.validate_query(tid, {"tenant_id": str(other)})


# ── list_policies ─────────────────────────────────────────────────────────────

async def test_list_policies_empty(svc: IsolationService) -> None:
    tid = uuid4()
    page = await svc.list_policies(tid)
    assert isinstance(page, PageResult)
    assert page.items == []
    assert page.total == 0


async def test_list_policies_returns_tenant_policies(
    svc: IsolationService, session: AsyncSession
) -> None:
    tid = uuid4()
    other_tid = uuid4()
    await _create_policy(session, tid, policy_type="strict")
    await _create_policy(session, other_tid, policy_type="partner")
    await session.commit()

    page = await svc.list_policies(tid)
    assert page.total == 1
    assert page.items[0].tenant_id == tid


# ── update_policy ─────────────────────────────────────────────────────────────

async def test_update_policy_name(svc: IsolationService, session: AsyncSession) -> None:
    tid = uuid4()
    policy = await _create_policy(session, tid)
    await session.commit()

    from app.schemas.isolation import PolicyUpdateRequest
    updated = await svc.update_policy(policy.id, PolicyUpdateRequest(name="new-name"))
    assert updated.name == "new-name"


async def test_update_policy_type_to_partner(
    svc: IsolationService, session: AsyncSession
) -> None:
    tid = uuid4()
    policy = await _create_policy(session, tid, policy_type="strict")
    await session.commit()

    partner_id = str(uuid4())
    from app.schemas.isolation import PolicyUpdateRequest
    updated = await svc.update_policy(
        policy.id,
        PolicyUpdateRequest(
            policy_type=PolicyType.PARTNER,
            allowed_partner_tenant_ids=[partner_id],
        ),
    )
    assert updated.policy_type == "partner"
    assert partner_id in [str(x) for x in updated.allowed_partner_tenant_ids]
