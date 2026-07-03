"""Tests for the trace-to-graph mining logic — the one piece of business
logic in this service that's actually intricate."""

from __future__ import annotations

from app.repositories.topology_repository import build_edges_from_traces


def test_empty_traces_yields_no_edges() -> None:
    assert build_edges_from_traces([]) == []


def test_trace_with_no_spans_key_is_ignored() -> None:
    assert build_edges_from_traces([{"trace_id": "abc"}]) == []


def test_single_cross_service_call_produces_one_edge() -> None:
    traces = [
        {
            "spans": [
                {"span_id": "1", "parent_span_id": None, "service_name": "api-gateway"},
                {"span_id": "2", "parent_span_id": "1", "service_name": "tenent"},
            ]
        }
    ]
    edges = build_edges_from_traces(traces)
    assert len(edges) == 1
    assert edges[0].caller == "api-gateway"
    assert edges[0].callee == "tenent"
    assert edges[0].call_count == 1


def test_same_service_parent_child_is_not_an_edge() -> None:
    traces = [
        {
            "spans": [
                {"span_id": "1", "parent_span_id": None, "service_name": "tenent"},
                {"span_id": "2", "parent_span_id": "1", "service_name": "tenent"},
            ]
        }
    ]
    assert build_edges_from_traces(traces) == []


def test_repeated_calls_across_traces_increment_call_count() -> None:
    def _trace() -> dict:
        return {
            "spans": [
                {"span_id": "1", "parent_span_id": None, "service_name": "api-gateway"},
                {"span_id": "2", "parent_span_id": "1", "service_name": "tenent"},
            ]
        }

    traces = [_trace(), _trace(), _trace()]
    edges = build_edges_from_traces(traces)
    assert len(edges) == 1
    assert edges[0].call_count == 3


def test_multi_hop_trace_produces_multiple_edges() -> None:
    traces = [
        {
            "spans": [
                {"span_id": "1", "parent_span_id": None, "service_name": "api-gateway"},
                {"span_id": "2", "parent_span_id": "1", "service_name": "tenent"},
                {"span_id": "3", "parent_span_id": "2", "service_name": "postgres"},
            ]
        }
    ]
    edges = {(e.caller, e.callee) for e in build_edges_from_traces(traces)}
    assert edges == {("api-gateway", "tenent"), ("tenent", "postgres")}


def test_span_with_unresolvable_parent_id_is_skipped() -> None:
    traces = [
        {
            "spans": [
                {"span_id": "2", "parent_span_id": "does-not-exist", "service_name": "tenent"},
            ]
        }
    ]
    assert build_edges_from_traces(traces) == []


def test_malformed_span_entries_are_ignored_safely() -> None:
    traces = [{"spans": ["not-a-dict", None, 42]}]
    assert build_edges_from_traces(traces) == []


def test_spans_key_not_a_list_is_ignored_safely() -> None:
    traces = [{"spans": "not-a-list"}]
    assert build_edges_from_traces(traces) == []
