"""Tests the Observability domain's topology mining now that it consumes
real, typed Span objects directly (in-process) instead of a raw dict shape
that crossed an HTTP boundary."""

from __future__ import annotations

from app.domains.observability.repositories.topology_repository import build_edges_from_traces
from app.domains.tracing.repositories.trace_repository import Span


def test_empty_traces_yields_no_edges() -> None:
    assert build_edges_from_traces([]) == []


def test_single_cross_service_call_produces_one_edge() -> None:
    spans = [
        Span(span_id="1", parent_span_id=None, service_name="api-gateway", name="GET /"),
        Span(span_id="2", parent_span_id="1", service_name="tenent", name="handle"),
    ]
    edges = build_edges_from_traces([spans])
    assert len(edges) == 1
    assert edges[0].caller == "api-gateway"
    assert edges[0].callee == "tenent"
    assert edges[0].call_count == 1


def test_same_service_parent_child_is_not_an_edge() -> None:
    spans = [
        Span(span_id="1", parent_span_id=None, service_name="tenent", name="a"),
        Span(span_id="2", parent_span_id="1", service_name="tenent", name="b"),
    ]
    assert build_edges_from_traces([spans]) == []


def test_repeated_calls_across_traces_increment_call_count() -> None:
    def _spans() -> list[Span]:
        return [
            Span(span_id="1", parent_span_id=None, service_name="api-gateway", name="a"),
            Span(span_id="2", parent_span_id="1", service_name="tenent", name="b"),
        ]

    edges = build_edges_from_traces([_spans(), _spans(), _spans()])
    assert len(edges) == 1
    assert edges[0].call_count == 3


def test_multi_hop_trace_produces_multiple_edges() -> None:
    spans = [
        Span(span_id="1", parent_span_id=None, service_name="api-gateway", name="a"),
        Span(span_id="2", parent_span_id="1", service_name="tenent", name="b"),
        Span(span_id="3", parent_span_id="2", service_name="postgres", name="c"),
    ]
    edges = {(e.caller, e.callee) for e in build_edges_from_traces([spans])}
    assert edges == {("api-gateway", "tenent"), ("tenent", "postgres")}


def test_span_with_unresolvable_parent_id_is_skipped() -> None:
    spans = [Span(span_id="2", parent_span_id="does-not-exist", service_name="tenent", name="b")]
    assert build_edges_from_traces([spans]) == []
