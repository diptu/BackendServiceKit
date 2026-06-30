"""Unit tests for CacheService using fakeredis."""

from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from app.domain.enums import CacheResult
from app.services.cache_service import CacheService


@pytest.fixture
def redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def svc(redis: FakeRedis) -> CacheService:
    return CacheService(redis)


@pytest.fixture
def null_svc() -> CacheService:
    """CacheService with no Redis — tests degraded mode."""
    return CacheService(None)


# ---------------------------------------------------------------------------
# Key building
# ---------------------------------------------------------------------------

def test_build_key_is_deterministic() -> None:
    k1 = CacheService.build_key("tenant_management", "/api/v1/tenants/abc", "limit=20")
    k2 = CacheService.build_key("tenant_management", "/api/v1/tenants/abc", "limit=20")
    assert k1 == k2


def test_build_key_differs_by_upstream() -> None:
    k1 = CacheService.build_key("tenant_management", "/api/v1/tenants/abc")
    k2 = CacheService.build_key("tenant_lifecycle", "/api/v1/tenants/abc")
    assert k1 != k2


def test_build_key_differs_by_path() -> None:
    k1 = CacheService.build_key("tenant_management", "/api/v1/tenants/abc")
    k2 = CacheService.build_key("tenant_management", "/api/v1/tenants/xyz")
    assert k1 != k2


def test_build_key_differs_by_query() -> None:
    k1 = CacheService.build_key("tenant_management", "/api/v1/tenants", "limit=10")
    k2 = CacheService.build_key("tenant_management", "/api/v1/tenants", "limit=20")
    assert k1 != k2


def test_build_key_has_prefix() -> None:
    k = CacheService.build_key("tenant_management", "/api/v1/tenants/abc")
    assert k.startswith("gw:")


# ---------------------------------------------------------------------------
# get / set / miss / hit
# ---------------------------------------------------------------------------

async def test_get_returns_miss_for_absent_key(svc: CacheService) -> None:
    value, result = await svc.get("gw:nonexistent:key")
    assert value is None
    assert result == CacheResult.MISS


async def test_set_then_get_returns_hit(svc: CacheService) -> None:
    key = CacheService.build_key("tenant_management", "/api/v1/tenants/abc")
    payload = b"hello cache"
    await svc.set(key, payload, ttl=60)
    value, result = await svc.get(key)
    assert result == CacheResult.HIT
    assert value == payload


async def test_set_respects_ttl(svc: CacheService, redis: FakeRedis) -> None:
    key = CacheService.build_key("tenant_management", "/api/v1/tenants/ttltest")
    await svc.set(key, b"data", ttl=120)
    ttl = await redis.ttl(key)
    assert 0 < ttl <= 120


# ---------------------------------------------------------------------------
# Tenant-scoped invalidation
# ---------------------------------------------------------------------------

async def test_invalidate_tenant_deletes_indexed_keys(svc: CacheService) -> None:
    tenant_id = "550e8400-e29b-41d4-a716-446655440000"
    upstream = "tenant_management"
    key = CacheService.build_key(upstream, f"/api/v1/tenants/{tenant_id}")

    await svc.set(key, b"data", ttl=300, tenant_id=tenant_id, upstream=upstream)

    deleted = await svc.invalidate_tenant(tenant_id, upstream)
    assert deleted >= 1

    value, result = await svc.get(key)
    assert result == CacheResult.MISS


async def test_invalidate_tenant_returns_zero_when_no_entries(svc: CacheService) -> None:
    deleted = await svc.invalidate_tenant("nonexistent-tenant", "tenant_management")
    assert deleted == 0


async def test_invalidate_all_upstreams(svc: CacheService) -> None:
    tenant_id = "test-tenant-multi"
    for upstream in ("tenant_management", "tenant_lifecycle"):
        key = CacheService.build_key(upstream, f"/api/v1/x/{tenant_id}")
        await svc.set(key, b"data", ttl=60, tenant_id=tenant_id, upstream=upstream)

    total = await svc.invalidate_all_upstreams(tenant_id, ["tenant_management", "tenant_lifecycle"])
    assert total >= 2


# ---------------------------------------------------------------------------
# Response encoding / decoding
# ---------------------------------------------------------------------------

def test_encode_decode_roundtrip() -> None:
    status = 200
    headers = {"content-type": "application/json", "x-request-id": "abc-123"}
    body = b'{"id": "abc", "status": "active"}'

    encoded = CacheService.encode_response(status, headers, body)
    dec_status, dec_headers, dec_body = CacheService.decode_response(encoded)

    assert dec_status == status
    assert dec_headers == headers
    assert dec_body == body


def test_encode_decode_empty_body() -> None:
    encoded = CacheService.encode_response(204, {}, b"")
    status, headers, body = CacheService.decode_response(encoded)
    assert status == 204
    assert headers == {}
    assert body == b""


# ---------------------------------------------------------------------------
# Degraded mode (Redis=None)
# ---------------------------------------------------------------------------

async def test_get_returns_error_when_redis_unavailable(null_svc: CacheService) -> None:
    _, result = await null_svc.get("any:key")
    assert result == CacheResult.ERROR


async def test_set_is_noop_when_redis_unavailable(null_svc: CacheService) -> None:
    await null_svc.set("any:key", b"data", ttl=60)  # must not raise


async def test_invalidate_returns_zero_when_redis_unavailable(null_svc: CacheService) -> None:
    deleted = await null_svc.invalidate_tenant("t1", "tenant_management")
    assert deleted == 0


async def test_ping_returns_false_when_redis_unavailable(null_svc: CacheService) -> None:
    assert await null_svc.ping() is False


async def test_ping_returns_true_when_redis_available(svc: CacheService) -> None:
    assert await svc.ping() is True
