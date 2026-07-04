"""Mines real service-call edges from the Tracing domain's own `Span`
objects — a genuine simplification enabled by in-process access (TODO.md
Decision #4): this no longer parses a raw, assumed-shape dict crossing an
HTTP boundary, it consumes the Tracing domain's real, typed `Span`
dataclass (itself parsed from Tempo's real OTLP-JSON full-trace response).

Algorithm unchanged: for each trace, build a `span_id -> service_name` map,
then for every span with a parent, if the parent's service differs from
the span's own service, that's one observed cross-service call. Same-
service parent/child spans are internal calls, not network hops, and are
deliberately excluded.
"""

from __future__ import annotations

from collections import Counter

from app.domains.observability.models import TopologyEdge
from app.domains.tracing.repositories.trace_repository import Span


def build_edges_from_traces(traces: list[list[Span]]) -> list[TopologyEdge]:
    edge_counts: Counter[tuple[str, str]] = Counter()

    for spans in traces:
        service_by_span_id = {s.span_id: s.service_name for s in spans if s.span_id}
        for span in spans:
            if not span.parent_span_id:
                continue
            parent_service = service_by_span_id.get(span.parent_span_id)
            if parent_service is None or parent_service == span.service_name:
                continue
            edge_counts[(parent_service, span.service_name)] += 1

    return [
        TopologyEdge(caller=caller, callee=callee, call_count=count)
        for (caller, callee), count in edge_counts.items()
    ]
