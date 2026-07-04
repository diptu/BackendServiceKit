from __future__ import annotations

from app.domains.health.models import FleetHealth, ServiceHealth
from app.domains.observability.services.topology_service import TopologyService
from app.domains.tracing.repositories.trace_repository import Span

_SPANS = [
    [
        Span(span_id="1", parent_span_id=None, service_name="api-gateway", name="a"),
        Span(span_id="2", parent_span_id="1", service_name="tenent", name="b"),
    ]
]


class _FakeTrace:
    def __init__(self, traces: list[list[Span]] | None) -> None:
        self._traces = traces

    async def recent_traces_with_spans(
        self, *, minutes: float = 15.0, limit: int = 20
    ) -> list[list[Span]] | None:
        return self._traces


class _FakeHealth:
    def __init__(self, fleet: FleetHealth | None) -> None:
        self._fleet = fleet

    async def get_fleet_health(self) -> FleetHealth | None:
        return self._fleet


async def test_get_dependencies_no_health_overlay() -> None:
    service = TopologyService(_FakeTrace(_SPANS), _FakeHealth(None))  # type: ignore[arg-type]
    graph = await service.get_dependencies()
    assert {n.name for n in graph.nodes} == {"api-gateway", "tenent"}
    assert all(n.reachable is None for n in graph.nodes)


async def test_get_topology_overlays_health() -> None:
    fleet = FleetHealth(
        overall_status="degraded",
        services=[
            ServiceHealth(name="api-gateway", base_url="", reachable=True),
            ServiceHealth(name="tenent", base_url="", reachable=False),
        ],
    )
    service = TopologyService(_FakeTrace(_SPANS), _FakeHealth(fleet))  # type: ignore[arg-type]
    graph = await service.get_topology()
    reachable_by_name = {n.name: n.reachable for n in graph.nodes}
    assert reachable_by_name == {"api-gateway": True, "tenent": False}


async def test_no_traces_yields_empty_graph() -> None:
    service = TopologyService(_FakeTrace(None), _FakeHealth(None))  # type: ignore[arg-type]
    graph = await service.get_dependencies()
    assert graph.nodes == []
    assert graph.edges == []
