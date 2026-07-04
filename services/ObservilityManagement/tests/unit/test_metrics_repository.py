from __future__ import annotations

from app.domains.metrics.repositories.metrics_repository import parse_instant_query_response


def test_parse_instant_query_response_empty() -> None:
    assert parse_instant_query_response({}) == []


def test_parse_instant_query_response_real_shape() -> None:
    raw = {
        "data": {
            "result": [
                {"metric": {"job": "tenent"}, "value": [1700000000, "1"]},
                {"metric": {"job": "api-gateway"}, "value": [1700000000, "0"]},
            ]
        }
    }
    samples = parse_instant_query_response(raw)
    assert len(samples) == 2
    by_job = {s.metric["job"]: s.value for s in samples}
    assert by_job == {"tenent": 1.0, "api-gateway": 0.0}


def test_parse_instant_query_response_malformed_entries_ignored_safely() -> None:
    raw = {"data": {"result": [{"metric": {}, "value": ["not-enough"]}, "not-a-dict"]}}
    assert parse_instant_query_response(raw) == []
