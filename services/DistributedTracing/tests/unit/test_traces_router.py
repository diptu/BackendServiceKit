from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.core.config import settings

_TEMPO = settings.tempo_base_url


def _search_response(trace_id: str = "abc123") -> dict:
    return {
        "traces": [
            {
                "traceID": trace_id,
                "rootServiceName": "tenent",
                "rootTraceName": "GET /api/v1/tenants",
                "startTimeUnixNano": "1700000000000000000",
                "durationMs": 42,
            }
        ]
    }


# Real base64-encoded span id captured from a live grafana/tempo:2.5.0
# response (see trace_repository.py's module docstring) — decodes to hex
# "5b0088c27869ca26". Using a plain string like "root" here would silently
# pass through base64.b64decode() too (it happens to be valid base64) and
# produce a different, wrong hex value, masking exactly the bug this test
# exists to catch.
_SPAN_ID_B64 = "WwCIwnhpyiY="
_SPAN_ID_HEX = "5b0088c27869ca26"


def _trace_response() -> dict:
    return {
        "batches": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "tenent"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "spanId": _SPAN_ID_B64,
                                "parentSpanId": "",
                                "name": "GET /api/v1/tenants",
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000000050000000",
                                "status": {"code": "STATUS_CODE_OK"},
                                "attributes": [],
                            }
                        ]
                    }
                ],
            }
        ]
    }


@respx.mock
async def test_search_traces(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/search").mock(return_value=Response(200, json=_search_response()))
    resp = await client.get("/api/v1/traces/search")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["trace_id"] == "abc123"


@respx.mock
async def test_traces_by_service(client: AsyncClient) -> None:
    route = respx.get(f"{_TEMPO}/api/search").mock(
        return_value=Response(200, json=_search_response())
    )
    resp = await client.get("/api/v1/traces/service/tenent")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["q"] == '{ resource.service.name="tenent" }'


@respx.mock
async def test_error_traces_builds_status_error_query(client: AsyncClient) -> None:
    route = respx.get(f"{_TEMPO}/api/search").mock(
        return_value=Response(200, json=_search_response())
    )
    resp = await client.get("/api/v1/traces/errors")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["q"] == "{ status=error }"


@respx.mock
async def test_slow_traces_builds_duration_query(client: AsyncClient) -> None:
    route = respx.get(f"{_TEMPO}/api/search").mock(
        return_value=Response(200, json=_search_response())
    )
    resp = await client.get("/api/v1/traces/slow?min_duration_ms=750")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["q"] == "{ duration>750ms }"


@respx.mock
async def test_get_trace_by_id(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/traces/abc123").mock(
        return_value=Response(200, json=_trace_response())
    )
    resp = await client.get("/api/v1/traces/abc123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["trace_id"] == "abc123"
    assert body["root_span_id"] == _SPAN_ID_HEX
    assert body["service_names"] == ["tenent"]
    assert len(body["spans"]) == 1


@respx.mock
async def test_get_trace_not_found_returns_404(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/traces/missing").mock(return_value=Response(404))
    resp = await client.get("/api/v1/traces/missing")
    assert resp.status_code == 404


@respx.mock
async def test_get_trace_timeline(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/traces/abc123").mock(
        return_value=Response(200, json=_trace_response())
    )
    resp = await client.get("/api/v1/traces/abc123/timeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["trace_id"] == "abc123"
    assert len(body["entries"]) == 1
    assert body["entries"][0]["relative_start_ms"] == 0


@respx.mock
async def test_get_trace_spans(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/traces/abc123").mock(
        return_value=Response(200, json=_trace_response())
    )
    resp = await client.get("/api/v1/traces/abc123/spans")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["spans"]) == 1
    assert body["spans"][0]["span_id"] == _SPAN_ID_HEX


async def test_delete_trace_returns_501(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/traces/abc123")
    assert resp.status_code == 501
    assert "Tempo has no concept" in resp.json()["detail"]


@respx.mock
async def test_export_traces_streams_ndjson(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/search").mock(return_value=Response(200, json=_search_response()))
    resp = await client.post("/api/v1/traces/export")
    assert resp.status_code == 200
    lines = [line for line in resp.text.strip().split("\n") if line]
    assert len(lines) == 1
    import json as _json

    parsed = _json.loads(lines[0])
    assert parsed["trace_id"] == "abc123"


@respx.mock
async def test_export_traces_full_mode_fetches_full_trace(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/search").mock(return_value=Response(200, json=_search_response()))
    respx.get(f"{_TEMPO}/api/traces/abc123").mock(
        return_value=Response(200, json=_trace_response())
    )
    resp = await client.post("/api/v1/traces/export?full=true")
    assert resp.status_code == 200
    import json as _json

    parsed = _json.loads(resp.text.strip())
    assert parsed["trace_id"] == "abc123"
    assert "spans" in parsed
