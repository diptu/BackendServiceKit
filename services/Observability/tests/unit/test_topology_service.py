from __future__ import annotations

from typing import Any

from app.services.topology_service import TopologyService

_TRACES = [
    {
        "spans": [
            {"span_id": "1", "parent_span_id": None, "service_name": "api-gateway"},
            {"span_id": "2", "parent_span_id": "1", "service_name": "tenent"},
        ]
    }
]


class _FakeTracingClient:
    def __init__(self, traces: list[dict[str, Any]] | None) -> None:
        self._traces = traces

    async def recent_traces(
        self, *, minutes: float = 15.0, limit: int = 50
    ) -> list[dict[str, Any]] | None:
        return self._traces


class _FakeHealthClient:
    def __init__(self, liveness: list[dict[str, Any]] | None) -> None:
        self._liveness = liveness

    async def liveness(self) -> list[dict[str, Any]] | None:
        return self._liveness


async def test_get_dependencies_returns_graph_with_no_health_overlay() -> None:
    service = TopologyService(_FakeTracingClient(_TRACES), _FakeHealthClient(None))  # type: ignore[arg-type]
    graph = await service.get_dependencies()
    assert {n.name for n in graph.nodes} == {"api-gateway", "tenent"}
    assert all(n.reachable is None for n in graph.nodes)
    assert len(graph.edges) == 1


async def test_get_topology_overlays_health() -> None:
    liveness = [
        {"service": "api-gateway", "reachable": True},
        {"service": "tenent", "reachable": False},
    ]
    service = TopologyService(_FakeTracingClient(_TRACES), _FakeHealthClient(liveness))  # type: ignore[arg-type]
    graph = await service.get_topology()
    reachable_by_name = {n.name: n.reachable for n in graph.nodes}
    assert reachable_by_name == {"api-gateway": True, "tenent": False}


async def test_get_topology_degrades_when_health_unreachable() -> None:
    service = TopologyService(_FakeTracingClient(_TRACES), _FakeHealthClient(None))  # type: ignore[arg-type]
    graph = await service.get_topology()
    assert all(n.reachable is None for n in graph.nodes)


async def test_no_traces_yields_empty_graph() -> None:
    service = TopologyService(_FakeTracingClient(None), _FakeHealthClient(None))  # type: ignore[arg-type]
    graph = await service.get_dependencies()
    assert graph.nodes == []
    assert graph.edges == []
