"""Mines real service-call edges from DistributedTracing's trace search
results — see TODO.md Decision #2. This is the one genuinely new data
source in this service: a real, observed topology, not static config or a
guess.

Each trace item is assumed to carry a `spans` list of
`{"span_id", "parent_span_id", "service_name"}` (see `tracing_client.py`'s
docstring for the shape-assumption caveat — unverified against a running
DistributedTracing until it's rebuilt, per Phase 0/Phase 12).

Algorithm: for each trace, build a `span_id -> service_name` map, then for
every span with a parent, if the parent's service differs from the span's
own service, that's one observed cross-service call (caller = parent's
service, callee = this span's service). Same-service parent/child spans
are internal calls, not network hops, and are deliberately excluded —
counting those would inflate the graph with self-loops that aren't real
topology.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.domain.observability import TopologyEdge


def build_edges_from_traces(traces: list[dict[str, Any]]) -> list[TopologyEdge]:
    edge_counts: Counter[tuple[str, str]] = Counter()

    for trace in traces:
        spans = trace.get("spans")
        if not isinstance(spans, list):
            continue

        service_by_span_id: dict[str, str] = {}
        for span in spans:
            if not isinstance(span, dict):
                continue
            span_id = span.get("span_id")
            service_name = span.get("service_name")
            if span_id is not None and service_name is not None:
                service_by_span_id[str(span_id)] = str(service_name)

        for span in spans:
            if not isinstance(span, dict):
                continue
            parent_id = span.get("parent_span_id")
            service_name = span.get("service_name")
            if not parent_id or service_name is None:
                continue
            parent_service = service_by_span_id.get(str(parent_id))
            if parent_service is None or parent_service == service_name:
                continue
            edge_counts[(parent_service, str(service_name))] += 1

    return [
        TopologyEdge(caller=caller, callee=callee, call_count=count)
        for (caller, callee), count in edge_counts.items()
    ]
