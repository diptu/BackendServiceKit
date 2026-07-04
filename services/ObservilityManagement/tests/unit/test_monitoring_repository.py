from __future__ import annotations

from app.domains.monitoring.repositories.monitoring_repository import (
    ServiceHealth,
    extract_dependency,
    first_non_none,
    overall_status,
    services_from_gateway_status,
)


def test_services_from_gateway_status_none() -> None:
    assert services_from_gateway_status(None) == []


def test_services_from_gateway_status_real_shape() -> None:
    raw = {
        "upstreams": [
            {
                "name": "tenent",
                "base_url": "http://tenent:8000",
                "reachable": True,
                "status_code": 200,
            },
            {"name": "observability-management", "base_url": "http://om:8000", "reachable": False},
        ]
    }
    services = services_from_gateway_status(raw)
    assert len(services) == 2
    assert services[0].reachable is True
    assert services[1].reachable is False


def test_extract_dependency_real_shape() -> None:
    ready_body = {
        "status": "degraded",
        "dependencies": [
            {"name": "postgres", "status": "up"},
            {"name": "redis", "status": "down"},
        ],
    }
    assert extract_dependency(ready_body, "postgres") is True
    assert extract_dependency(ready_body, "redis") is False
    assert extract_dependency(ready_body, "rabbitmq") is None


def test_extract_dependency_none_body() -> None:
    assert extract_dependency(None, "postgres") is None


def test_first_non_none() -> None:
    assert first_non_none(None, None, True) is True
    assert first_non_none(False, True) is False
    assert first_non_none(None, None) is None


def test_overall_status_healthy() -> None:
    services = [ServiceHealth(name="a", base_url="", reachable=True)]
    assert overall_status(services) == "healthy"


def test_overall_status_degraded() -> None:
    services = [
        ServiceHealth(name="a", base_url="", reachable=True),
        ServiceHealth(name="b", base_url="", reachable=False),
    ]
    assert overall_status(services) == "degraded"


def test_overall_status_unhealthy() -> None:
    services = [ServiceHealth(name="a", base_url="", reachable=False)]
    assert overall_status(services) == "unhealthy"


def test_overall_status_unknown_when_empty() -> None:
    assert overall_status([]) == "unknown"
