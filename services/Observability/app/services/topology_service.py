"""Composes TracingClient + topology_repository (TODO.md Decision #2) and
HealthClient (Decision #3)."""

from __future__ import annotations

from app.domain.observability import TopologyGraph, TopologyNode
from app.infrastructure.siblings.health_client import HealthClient
from app.infrastructure.siblings.tracing_client import TracingClient
from app.repositories.topology_repository import build_edges_from_traces


class TopologyService:
    def __init__(self, tracing_client: TracingClient, health_client: HealthClient) -> None:
        self._tracing = tracing_client
        self._health = health_client

    async def get_dependencies(self, *, minutes: float = 15.0) -> TopologyGraph:
        """Decision #2 alone — the raw observed call graph, no health overlay."""
        traces = await self._tracing.recent_traces(minutes=minutes)
        edges = build_edges_from_traces(traces) if traces else []
        node_names = sorted({e.caller for e in edges} | {e.callee for e in edges})
        nodes = [TopologyNode(name=name, reachable=None) for name in node_names]
        return TopologyGraph(nodes=nodes, edges=edges)

    async def get_topology(self, *, minutes: float = 15.0) -> TopologyGraph:
        """Decision #3 — Decision #2's graph with live health overlaid from HealthCheck."""
        graph = await self.get_dependencies(minutes=minutes)
        liveness = await self._health.liveness()
        reachable_by_name: dict[str, bool] = {}
        if liveness:
            for item in liveness:
                name = item.get("service")
                if name is not None:
                    reachable_by_name[str(name)] = bool(item.get("reachable"))
        nodes = [
            TopologyNode(name=n.name, reachable=reachable_by_name.get(n.name)) for n in graph.nodes
        ]
        return TopologyGraph(nodes=nodes, edges=graph.edges)
