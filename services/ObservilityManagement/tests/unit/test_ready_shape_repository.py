"""One test per real /ready shape this repo's remaining external targets
(Tenent, APIGateway) plus this service's own /ready can produce."""

from __future__ import annotations

from app.domains.health.models import DependencyStatus
from app.domains.health.repositories.ready_shape_repository import normalize_ready_body


def test_none_body_normalizes_to_empty() -> None:
    assert normalize_ready_body(None) == []


def test_self_shape_no_dependencies() -> None:
    assert normalize_ready_body({"status": "ok"}) == []


def test_tenent_list_shape() -> None:
    raw = {
        "status": "degraded",
        "dependencies": [
            {"name": "postgres", "status": "up", "latency_ms": 1.2, "error": None},
            {"name": "redis", "status": "down", "latency_ms": None, "error": "connection refused"},
        ],
    }
    deps = normalize_ready_body(raw)
    by_name = {d.name: d for d in deps}
    assert by_name["postgres"].status == "up"
    assert by_name["redis"].error == "connection refused"


def test_api_gateway_flat_string_shape() -> None:
    raw = {"status": "degraded", "redis": "ok", "rabbitmq": "unavailable"}
    deps = normalize_ready_body(raw)
    by_name = {d.name: d.status for d in deps}
    assert by_name == {"redis": "up", "rabbitmq": "down"}


def test_flat_boolean_shape() -> None:
    raw = {"status": "ok", "loki": True}
    deps = normalize_ready_body(raw)
    assert deps == [DependencyStatus(name="loki", status="up")]


def test_unrecognized_status_value_normalizes_to_unknown() -> None:
    raw = {"status": "ok", "dependencies": {"weird": "sideways"}}
    deps = normalize_ready_body(raw)
    assert deps[0].status == "unknown"


def test_non_dict_dependencies_value_is_ignored_safely() -> None:
    raw = {"status": "ok", "dependencies": "not-a-list-or-dict"}
    assert normalize_ready_body(raw) == []
