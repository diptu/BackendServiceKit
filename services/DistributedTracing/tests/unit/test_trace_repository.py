from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidTraceQLError
from app.repositories.trace_repository import build_traceql, parse_search_results, parse_trace


def test_build_traceql_no_filters_returns_catchall() -> None:
    assert build_traceql() == "{}"


def test_build_traceql_service_is_resource_attribute() -> None:
    assert build_traceql(service="tenent") == '{ resource.service.name="tenent" }'


def test_build_traceql_status_is_intrinsic_field() -> None:
    assert build_traceql(status="error") == "{ status=error }"


def test_build_traceql_rejects_invalid_status() -> None:
    with pytest.raises(InvalidTraceQLError):
        build_traceql(status="bogus")


def test_build_traceql_min_duration_ms() -> None:
    assert build_traceql(min_duration_ms=500) == "{ duration>500ms }"


def test_build_traceql_tenant_id_uses_dotted_span_attribute() -> None:
    # Matches the key set_tenant_span_attributes() would use if ever wired in —
    # currently a no-op since no span carries this attribute (see TODO.md Decision #3).
    assert build_traceql(tenant_id="t1") == '{ span."tenant.id"="t1" }'


def test_build_traceql_q_is_a_span_attribute_filter() -> None:
    assert build_traceql(query_text="http.method=POST") == '{ span.http.method="POST" }'


def test_build_traceql_q_supports_multiple_comma_separated_pairs() -> None:
    result = build_traceql(query_text="a=1,b=2")
    assert result == '{ span.a="1" && span.b="2" }'


def test_build_traceql_q_rejects_missing_equals() -> None:
    with pytest.raises(InvalidTraceQLError):
        build_traceql(query_text="no-equals-sign")


def test_build_traceql_combines_clauses_with_and() -> None:
    result = build_traceql(service="tenent", status="error", min_duration_ms=100)
    assert result == '{ resource.service.name="tenent" && status=error && duration>100ms }'


def test_build_traceql_escapes_quotes_in_service_name() -> None:
    assert build_traceql(service='ten"ent') == '{ resource.service.name="ten\\"ent" }'


def test_parse_search_results_extracts_summaries() -> None:
    data = {
        "traces": [
            {
                "traceID": "abc123",
                "rootServiceName": "tenent",
                "rootTraceName": "GET /api/v1/tenants",
                "startTimeUnixNano": "1700000000000000000",
                "durationMs": 42,
            }
        ]
    }
    summaries = parse_search_results(data)
    assert len(summaries) == 1
    assert summaries[0].trace_id == "abc123"
    assert summaries[0].root_service_name == "tenent"
    assert summaries[0].duration_ms == 42


def test_parse_search_results_sorts_newest_first() -> None:
    data = {
        "traces": [
            {"traceID": "a", "startTimeUnixNano": "100"},
            {"traceID": "b", "startTimeUnixNano": "300"},
            {"traceID": "c", "startTimeUnixNano": "200"},
        ]
    }
    summaries = parse_search_results(data)
    assert [s.trace_id for s in summaries] == ["b", "c", "a"]


def test_parse_search_results_empty() -> None:
    assert parse_search_results({}) == []


def test_parse_trace_extracts_spans_and_service_name() -> None:
    data = {
        "batches": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "tenent"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "spanId": "span1",
                                "parentSpanId": "",
                                "name": "GET /health",
                                "startTimeUnixNano": "100",
                                "endTimeUnixNano": "200",
                                "status": {"code": "STATUS_CODE_OK"},
                                "attributes": [
                                    {"key": "http.status_code", "value": {"intValue": "200"}}
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }
    trace = parse_trace(data, trace_id="abc123")
    assert trace.trace_id == "abc123"
    assert len(trace.spans) == 1
    span = trace.spans[0]
    assert span.span_id == "span1"
    assert span.parent_span_id is None
    assert span.service == "tenent"
    assert span.status == "ok"
    assert span.duration_ns == 100
    assert span.attributes["http.status_code"] == 200


def test_parse_trace_accepts_otlp_native_field_names() -> None:
    # resourceSpans/instrumentationLibrarySpans instead of batches/scopeSpans
    data = {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "instrumentationLibrarySpans": [
                    {
                        "spans": [
                            {
                                "spanId": "span1",
                                "name": "op",
                                "startTimeUnixNano": "0",
                                "endTimeUnixNano": "0",
                            }
                        ]
                    }
                ],
            }
        ]
    }
    trace = parse_trace(data, trace_id="xyz")
    assert len(trace.spans) == 1
    assert trace.spans[0].status == "unset"


def test_parse_trace_empty_batches_yields_no_spans() -> None:
    trace = parse_trace({}, trace_id="none")
    assert trace.spans == []


def test_parse_trace_decodes_base64_span_ids_to_hex() -> None:
    # Verified against a real grafana/tempo:2.5.0 container: /api/traces/{id}
    # encodes spanId/parentSpanId as base64 (OTLP-JSON bytes encoding), while
    # /api/search encodes traceID/spanID as plain hex for the *same* span.
    # "WwCIwnhpyiY=" is the real base64 Tempo returned; "5b0088c27869ca26" is
    # the hex it decodes to, which matches what /api/search returned for the
    # identical span. Getting this wrong would silently break cross-referencing
    # a span_id from this service's /traces/{id} response against /traces/search
    # results or Tempo's own UI.
    data = {
        "batches": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "spanId": "WwCIwnhpyiY=",
                                "parentSpanId": "WwCIwnhpyiY=",
                                "name": "op",
                                "startTimeUnixNano": "0",
                                "endTimeUnixNano": "0",
                            }
                        ]
                    }
                ],
            }
        ]
    }
    trace = parse_trace(data, trace_id="t1")
    span = trace.spans[0]
    assert span.span_id == "5b0088c27869ca26"
    assert span.parent_span_id == "5b0088c27869ca26"


def test_parse_trace_empty_parent_span_id_is_none() -> None:
    data = {
        "batches": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "spanId": "WwCIwnhpyiY=",
                                "parentSpanId": "",
                                "name": "root",
                                "startTimeUnixNano": "0",
                                "endTimeUnixNano": "0",
                            }
                        ]
                    }
                ],
            }
        ]
    }
    trace = parse_trace(data, trace_id="t1")
    assert trace.spans[0].parent_span_id is None
