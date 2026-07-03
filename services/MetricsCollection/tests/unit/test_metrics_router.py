from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.core.config import settings

_PROM = settings.prometheus_base_url
_PGW = settings.pushgateway_base_url


def _vector_response(value: str = "42", labels: dict | None = None) -> dict:
    metric = {"__name__": "isolation_decisions_total"}
    if labels:
        metric.update(labels)
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [{"metric": metric, "value": [1700000000, value]}],
        },
    }


@respx.mock
async def test_list_metrics(client: AsyncClient) -> None:
    respx.get(f"{_PROM}/api/v1/label/__name__/values").mock(
        return_value=Response(
            200, json={"status": "success", "data": ["up", "isolation_decisions_total"]}
        )
    )
    resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert "up" in body["names"]


@respx.mock
async def test_list_metrics_with_prefix_filter(client: AsyncClient) -> None:
    respx.get(f"{_PROM}/api/v1/label/__name__/values").mock(
        return_value=Response(
            200, json={"status": "success", "data": ["isolation_decisions_total", "up"]}
        )
    )
    resp = await client.get("/api/v1/metrics?prefix=isolation")
    body = resp.json()
    assert body["names"] == ["isolation_decisions_total"]


@respx.mock
async def test_query_metric(client: AsyncClient) -> None:
    route = respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(200, json=_vector_response())
    )
    resp = await client.get("/api/v1/metrics/query?metric=isolation_decisions_total")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["value"] == 42.0
    assert route.calls.last.request.url.params["query"] == "isolation_decisions_total"


@respx.mock
async def test_query_metric_with_job_filter(client: AsyncClient) -> None:
    route = respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(200, json=_vector_response())
    )
    resp = await client.get("/api/v1/metrics/query?metric=up&job=tenent")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["query"] == 'up{job="tenent"}'


@respx.mock
async def test_metric_history(client: AsyncClient) -> None:
    respx.get(f"{_PROM}/api/v1/query_range").mock(
        return_value=Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [{"metric": {"__name__": "up"}, "values": [[100, "1"], [160, "1"]]}],
                },
            },
        )
    )
    resp = await client.get("/api/v1/metrics/history?metric=up")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["values"] == [[100.0, 1.0], [160.0, 1.0]]


@respx.mock
async def test_metric_by_service_uses_job_label(client: AsyncClient) -> None:
    route = respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(200, json=_vector_response())
    )
    resp = await client.get("/api/v1/metrics/service/tenent?metric=isolation_decisions_total")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["query"] == 'isolation_decisions_total{job="tenent"}'


@respx.mock
async def test_metric_by_tenant_is_forward_compatible_filter(client: AsyncClient) -> None:
    route = respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(200, json=_vector_response())
    )
    resp = await client.get("/api/v1/metrics/tenant/t1?metric=up")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["query"] == 'up{tenant_id="t1"}'


@respx.mock
async def test_top_metrics(client: AsyncClient) -> None:
    route = respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(200, json=_vector_response())
    )
    resp = await client.get("/api/v1/metrics/top?metric=isolation_decisions_total&n=3")
    assert resp.status_code == 200
    assert route.calls.last.request.url.params["query"] == "topk(3, isolation_decisions_total)"


@respx.mock
async def test_system_metrics_queries_both_process_metrics(client: AsyncClient) -> None:
    route = respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(
            200, json={"status": "success", "data": {"resultType": "vector", "result": []}}
        )
    )
    resp = await client.get("/api/v1/metrics/system")
    assert resp.status_code == 200
    queried = {call.request.url.params["query"] for call in route.calls}
    assert queried == {"process_resident_memory_bytes", "process_cpu_seconds_total"}


@respx.mock
async def test_push_metric(client: AsyncClient) -> None:
    route = respx.post(f"{_PGW}/metrics/job/external").mock(return_value=Response(200))
    resp = await client.post(
        "/api/v1/metrics", json={"metric": "cpu_usage", "value": 67, "job": "external"}
    )
    assert resp.status_code == 202
    assert resp.json() == {"accepted": 1}
    assert route.called
    assert b"cpu_usage 67.0" in route.calls.last.request.content


@respx.mock
async def test_push_metrics_bulk(client: AsyncClient) -> None:
    respx.post(f"{_PGW}/metrics/job/job1").mock(return_value=Response(200))
    respx.post(f"{_PGW}/metrics/job/job2").mock(return_value=Response(200))
    resp = await client.post(
        "/api/v1/metrics/bulk",
        json={
            "items": [
                {"metric": "a", "value": 1, "job": "job1"},
                {"metric": "b", "value": 2, "job": "job2"},
            ]
        },
    )
    assert resp.status_code == 202
    assert resp.json() == {"accepted": 2}


async def test_bulk_push_over_limit_is_rejected(client: AsyncClient) -> None:
    items = [{"metric": "a", "value": 1}] * (settings.metrics_bulk_max_items + 1)
    resp = await client.post("/api/v1/metrics/bulk", json={"items": items})
    assert resp.status_code == 422


@respx.mock
async def test_delete_metrics_for_job(client: AsyncClient) -> None:
    route = respx.delete(f"{_PGW}/metrics/job/myjob").mock(return_value=Response(200))
    resp = await client.delete("/api/v1/metrics/myjob")
    assert resp.status_code == 200
    assert resp.json() == {"job": "myjob", "labels": {}}
    assert route.called


async def test_delete_metrics_without_job_returns_409(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/metrics")
    assert resp.status_code == 409
    assert "scraped series" in resp.json()["detail"] or "Pushgateway" in resp.json()["detail"]
