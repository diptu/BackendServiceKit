"""Composes the Tracing domain's real span data (topology_repository,
TODO.md Decision #2) with the Health domain's live reachability (Decision
#3) — in-process, no HTTP hop."""

from __future__ import annotations

from app.domains.health.services.health_service import HealthService
from app.domains.observability.models import TopologyGraph, TopologyNode
from app.domains.observability.repositories.topology_repository import build_edges_from_traces
from app.domains.observability.services.safe_call import safe_call
from app.domains.tracing.services.trace_query_service import TraceQueryService


class TopologyService:
    def __init__(self, trace_service: TraceQueryService, health_service: HealthService) -> None:
        self._traces = trace_service
        self._health = health_service

    async def get_dependencies(self, *, minutes: float = 15.0) -> TopologyGraph:
        """Decision #2 alone — the raw observed call graph, no health overlay."""
        traces = await safe_call(self._traces.recent_traces_with_spans(minutes=minutes))
        edges = build_edges_from_traces(traces) if traces else []
        node_names = sorted({e.caller for e in edges} | {e.callee for e in edges})
        nodes = [TopologyNode(name=name, reachable=None) for name in node_names]
        return TopologyGraph(nodes=nodes, edges=edges)

    async def get_topology(self, *, minutes: float = 15.0) -> TopologyGraph:
        """Decision #3 — Decision #2's graph with live health overlaid."""
        graph = await self.get_dependencies(minutes=minutes)
        fleet = await safe_call(self._health.get_fleet_health())
        reachable_by_name = {s.name: s.reachable for s in fleet.services} if fleet else {}
        nodes = [
            TopologyNode(name=n.name, reachable=reachable_by_name.get(n.name)) for n in graph.nodes
        ]
        return TopologyGraph(nodes=nodes, edges=graph.edges)
