"""Unit tests for isolation API endpoints — service layer mocked."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.enums import IsolationDecision
from app.domain.exceptions import ContextResolutionError
from app.main import app
from app.schemas.isolation import (
    CheckAccessResponse,
    ResolveContextResponse,
    ValidateResourceResponse,
    ValidateResponse,
)


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_validate_same_tenant_allow(client: AsyncClient, mocker: object) -> None:
    tid = str(uuid4())
    rid = str(uuid4())
    mock_resp = ValidateResponse(
        decision=IsolationDecision.ALLOW,
        violations=[],
        caller_tenant_id=tid,  # type: ignore[arg-type]
        resource_type="document",
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.validate",
        return_value=mock_resp,
    )
    resp = await client.post(
        "/api/v1/isolation/validate",
        json={"caller_tenant_id": tid, "resource_ids": [rid], "resource_type": "document"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"
    assert resp.json()["violations"] == []


async def test_validate_wrong_tenant_deny(client: AsyncClient, mocker: object) -> None:
    tid = str(uuid4())
    rid = str(uuid4())
    mock_resp = ValidateResponse(
        decision=IsolationDecision.DENY,
        violations=[rid],
        caller_tenant_id=tid,  # type: ignore[arg-type]
        resource_type="document",
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.validate",
        return_value=mock_resp,
    )
    resp = await client.post(
        "/api/v1/isolation/validate",
        json={"caller_tenant_id": tid, "resource_ids": [rid], "resource_type": "document"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"
    assert rid in resp.json()["violations"]


async def test_check_access_same_tenant(client: AsyncClient, mocker: object) -> None:
    tid = str(uuid4())
    mock_resp = CheckAccessResponse(
        decision=IsolationDecision.ALLOW,
        reason="same-tenant",
        caller_tenant_id=tid,  # type: ignore[arg-type]
        target_tenant_id=tid,  # type: ignore[arg-type]
        resource_id="res1",
        resource_type="document",
        action="read",
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.check_access",
        return_value=mock_resp,
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.cache_get",
        return_value=None,
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.cache_set",
        return_value=None,
    )
    resp = await client.post(
        "/api/v1/isolation/check-access",
        json={
            "caller_tenant_id": tid,
            "target_tenant_id": tid,
            "resource_id": "res1",
            "resource_type": "document",
            "action": "read",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


async def test_check_access_cross_tenant_strict(client: AsyncClient, mocker: object) -> None:
    caller = str(uuid4())
    target = str(uuid4())
    mock_resp = CheckAccessResponse(
        decision=IsolationDecision.DENY,
        reason="strict policy",
        caller_tenant_id=caller,  # type: ignore[arg-type]
        target_tenant_id=target,  # type: ignore[arg-type]
        resource_id="res1",
        resource_type="document",
        action="read",
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.check_access",
        return_value=mock_resp,
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.cache_get",
        return_value=None,
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.cache_set",
        return_value=None,
    )
    resp = await client.post(
        "/api/v1/isolation/check-access",
        json={
            "caller_tenant_id": caller,
            "target_tenant_id": target,
            "resource_id": "res1",
            "resource_type": "document",
            "action": "read",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


async def test_resolve_context_valid_token(client: AsyncClient, mocker: object) -> None:
    tid = str(uuid4())
    mock_resp = ResolveContextResponse(
        tenant_id=tid,  # type: ignore[arg-type]
        user_id=None,
        token_type="bearer",
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.resolve_context",
        return_value=mock_resp,
    )
    resp = await client.post(
        "/api/v1/isolation/resolve-context",
        json={"token": "fake.jwt.token"},
    )
    assert resp.status_code == 200
    assert resp.json()["tenant_id"] == tid
    assert resp.json()["token_type"] == "bearer"


async def test_resolve_context_invalid_token(client: AsyncClient, mocker: object) -> None:
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.resolve_context",
        side_effect=ContextResolutionError("bad token"),
    )
    resp = await client.post(
        "/api/v1/isolation/resolve-context",
        json={"token": "invalid"},
    )
    assert resp.status_code == 401


async def test_validate_resource_found(client: AsyncClient, mocker: object) -> None:
    tid = str(uuid4())
    mock_resp = ValidateResourceResponse(
        decision=IsolationDecision.ALLOW,
        owner_tenant_id=tid,  # type: ignore[arg-type]
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.validate_resource",
        return_value=mock_resp,
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.cache_get",
        return_value=None,
    )
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.cache.redis_cache.cache_set",
        return_value=None,
    )
    resp = await client.post(
        "/api/v1/isolation/validate-resource",
        json={"caller_tenant_id": tid, "resource_id": "res1", "resource_type": "document"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


async def test_validate_query_valid(client: AsyncClient, mocker: object) -> None:
    from app.schemas.isolation import ValidateQueryResponse

    tid = str(uuid4())
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.validate_query",
        return_value=ValidateQueryResponse(is_valid=True, reason=None),
    )
    resp = await client.post(
        "/api/v1/isolation/validate-query",
        json={"caller_tenant_id": tid, "query_filter": {"tenant_id": tid}},
    )
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True


async def test_validate_query_missing_tenant_id(client: AsyncClient) -> None:
    tid = str(uuid4())
    resp = await client.post(
        "/api/v1/isolation/validate-query",
        json={"caller_tenant_id": tid, "query_filter": {"other": "val"}},
    )
    assert resp.status_code == 422


async def test_list_policies(client: AsyncClient, mocker: object) -> None:
    from app.repositories.base import PageResult

    tid = str(uuid4())
    mocker.patch(  # type: ignore[attr-defined]
        "app.services.isolation_service.IsolationService.list_policies",
        return_value=PageResult(items=[], total=0, has_more=False, next_cursor=None),
    )
    resp = await client.get(f"/api/v1/isolation/policies?tenant_id={tid}")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0
