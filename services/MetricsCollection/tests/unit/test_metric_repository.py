from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidPromQLError
from app.repositories.metric_repository import (
    build_promql,
    build_topk_promql,
    parse_query_result,
    parse_range_result,
)


def test_build_promql_metric_only() -> None:
    assert build_promql(metric="isolation_decisions_total") == "isolation_decisions_total"


def test_build_promql_requires_metric() -> None:
    with pytest.raises(InvalidPromQLError):
        build_promql(metric="")


def test_build_promql_job_filter() -> None:
    result = build_promql(metric="up", job="tenent")
    assert result == 'up{job="tenent"}'


def test_build_promql_tenant_id_is_forward_compatible_no_op_filter() -> None:
    # No real metric carries this label today (see TODO.md Decision #3) —
    # still built so it starts working the moment one does.
    result = build_promql(metric="up", tenant_id="t1")
    assert result == 'up{tenant_id="t1"}'


def test_build_promql_q_is_a_generic_label_filter() -> None:
    result = build_promql(metric="up", query_text="decision=allow")
    assert result == 'up{decision="allow"}'


def test_build_promql_q_supports_multiple_comma_separated_pairs() -> None:
    result = build_promql(metric="up", query_text="a=1,b=2")
    assert result == 'up{a="1",b="2"}'


def test_build_promql_combines_job_tenant_and_q() -> None:
    result = build_promql(metric="up", job="tenent", tenant_id="t1", query_text="decision=allow")
    assert result == 'up{job="tenent",tenant_id="t1",decision="allow"}'


def test_build_promql_q_rejects_missing_equals() -> None:
    with pytest.raises(InvalidPromQLError):
        build_promql(metric="up", query_text="no-equals-sign")


def test_build_promql_escapes_quotes() -> None:
    result = build_promql(metric="up", job='ten"ent')
    assert result == 'up{job="ten\\"ent"}'


def test_build_topk_promql() -> None:
    assert (
        build_topk_promql(metric="isolation_decisions_total", n=5)
        == "topk(5, isolation_decisions_total)"
    )


def test_build_topk_promql_rejects_non_positive_n() -> None:
    with pytest.raises(InvalidPromQLError):
        build_topk_promql(metric="up", n=0)


def test_parse_query_result_vector() -> None:
    data = {
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": "isolation_decisions_total", "decision": "allow"},
                    "value": [1700000000, "42"],
                }
            ],
        }
    }
    samples = parse_query_result(data)
    assert len(samples) == 1
    assert samples[0].metric_name == "isolation_decisions_total"
    assert samples[0].labels == {"decision": "allow"}
    assert samples[0].value == 42.0
    assert samples[0].timestamp_s == 1700000000.0


def test_parse_query_result_scalar_has_no_labels() -> None:
    data = {"data": {"resultType": "scalar", "result": [1700000000, "1"]}}
    samples = parse_query_result(data)
    assert len(samples) == 1
    assert samples[0].metric_name == ""
    assert samples[0].labels == {}
    assert samples[0].value == 1.0


def test_parse_query_result_unknown_result_type_returns_empty() -> None:
    assert parse_query_result({"data": {"resultType": "matrix", "result": []}}) == []


def test_parse_query_result_empty_data() -> None:
    assert parse_query_result({}) == []


def test_parse_range_result_matrix() -> None:
    data = {
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": "up", "job": "tenent"},
                    "values": [[100, "1"], [160, "1"], [220, "0"]],
                }
            ],
        }
    }
    series = parse_range_result(data)
    assert len(series) == 1
    assert series[0].metric_name == "up"
    assert series[0].labels == {"job": "tenent"}
    assert series[0].values == [(100.0, 1.0), (160.0, 1.0), (220.0, 0.0)]


def test_parse_range_result_empty() -> None:
    assert parse_range_result({}) == []
