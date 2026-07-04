"""Tests for the real OTLP-JSON full-trace parsing — the corrected shape
this merge closes (see tempo_client.py's docstring)."""

from __future__ import annotations

from app.domains.tracing.repositories.trace_repository import (
    parse_full_trace_response,
    parse_search_response,
)


def test_parse_search_response_empty() -> None:
    assert parse_search_response({}) == []


def test_parse_search_response_real_shape() -> None:
    raw = {
        "traces": [
            {
                "traceID": "abc123",
                "rootServiceName": "api-gateway",
                "rootTraceName": "GET /api/v1/tenants",
                "startTimeUnixNano": "1700000000000000000",
                "durationMs": 42,
            }
        ]
    }
    summaries = parse_search_response(raw)
    assert len(summaries) == 1
    assert summaries[0].trace_id == "abc123"
    assert summaries[0].root_service == "api-gateway"
    assert summaries[0].duration_ms == 42
    assert summaries[0].start_time.startswith("2023-11-14")


def test_parse_full_trace_response_extracts_service_name_and_spans() -> None:
    raw = {
        "batches": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "api-gateway"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {"spanId": "1", "parentSpanId": None, "name": "GET /"},
                            {"spanId": "2", "parentSpanId": "1", "name": "call tenent"},
                        ]
                    }
                ],
            },
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "tenent"}}]
                },
                "scopeSpans": [{"spans": [{"spanId": "3", "parentSpanId": "2", "name": "handle"}]}],
            },
        ]
    }
    spans = parse_full_trace_response(raw)
    assert len(spans) == 3
    by_id = {s.span_id: s for s in spans}
    assert by_id["1"].service_name == "api-gateway"
    assert by_id["2"].service_name == "api-gateway"
    assert by_id["3"].service_name == "tenent"
    assert by_id["3"].parent_span_id == "2"


def test_parse_full_trace_response_missing_service_name_defaults_unknown() -> None:
    raw = {"batches": [{"resource": {}, "scopeSpans": [{"spans": [{"spanId": "1"}]}]}]}
    spans = parse_full_trace_response(raw)
    assert spans[0].service_name == "unknown"


def test_parse_full_trace_response_malformed_batches_ignored_safely() -> None:
    assert parse_full_trace_response({"batches": "not-a-list"}) == []
    assert parse_full_trace_response({}) == []
