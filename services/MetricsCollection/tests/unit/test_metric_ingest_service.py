from __future__ import annotations

import pytest

from app.domain.exceptions import BulkPushLimitExceededError
from app.schemas.metric import MetricPushCreate
from app.services.metric_ingest_service import _build_exposition_text


def test_exposition_text_single_metric_no_labels() -> None:
    text = _build_exposition_text([MetricPushCreate(metric="cpu_usage", value=67, job="external")])
    assert text == "# TYPE cpu_usage gauge\ncpu_usage 67.0\n"


def test_exposition_text_with_labels() -> None:
    items = [
        MetricPushCreate(metric="cpu_usage", value=67, job="external", labels={"region": "us-east"})
    ]
    text = _build_exposition_text(items)
    assert text == '# TYPE cpu_usage gauge\ncpu_usage{region="us-east"} 67.0\n'


def test_exposition_text_declares_type_once_per_metric_name() -> None:
    items = [
        MetricPushCreate(metric="cpu_usage", value=10, labels={"region": "us-east"}),
        MetricPushCreate(metric="cpu_usage", value=20, labels={"region": "eu-west"}),
    ]
    text = _build_exposition_text(items)
    assert text.count("# TYPE cpu_usage gauge") == 1
    assert 'cpu_usage{region="us-east"} 10.0' in text
    assert 'cpu_usage{region="eu-west"} 20.0' in text


def test_exposition_text_counter_type() -> None:
    text = _build_exposition_text(
        [MetricPushCreate(metric="jobs_completed_total", value=3, metric_type="counter")]
    )
    assert "# TYPE jobs_completed_total counter" in text


def test_exposition_text_escapes_label_values() -> None:
    items = [MetricPushCreate(metric="m", value=1, labels={"k": 'has"quote'})]
    text = _build_exposition_text(items)
    assert 'k="has\\"quote"' in text


class _FakePushgatewayClient:
    def __init__(self) -> None:
        self.pushed: list[tuple[str, dict[str, str], str]] = []
        self.deleted: list[tuple[str, dict[str, str]]] = []

    async def push(self, *, job: str, labels: dict[str, str], exposition_text: str) -> None:
        self.pushed.append((job, labels, exposition_text))

    async def delete(self, *, job: str, labels: dict[str, str]) -> None:
        self.deleted.append((job, labels))


async def test_push_bulk_groups_by_job() -> None:
    from app.services.metric_ingest_service import MetricIngestService

    fake = _FakePushgatewayClient()
    svc = MetricIngestService(fake, max_bulk_items=10)  # type: ignore[arg-type]
    items = [
        MetricPushCreate(metric="a", value=1, job="job1"),
        MetricPushCreate(metric="b", value=2, job="job2"),
        MetricPushCreate(metric="c", value=3, job="job1"),
    ]
    accepted = await svc.push_bulk(items)
    assert accepted == 3
    assert len(fake.pushed) == 2  # one push per distinct job
    jobs_pushed = {p[0] for p in fake.pushed}
    assert jobs_pushed == {"job1", "job2"}


async def test_push_bulk_over_limit_raises() -> None:
    from app.services.metric_ingest_service import MetricIngestService

    fake = _FakePushgatewayClient()
    svc = MetricIngestService(fake, max_bulk_items=2)  # type: ignore[arg-type]
    items = [MetricPushCreate(metric="a", value=1)] * 3
    with pytest.raises(BulkPushLimitExceededError):
        await svc.push_bulk(items)


async def test_delete_calls_pushgateway_client() -> None:
    from app.services.metric_ingest_service import MetricIngestService

    fake = _FakePushgatewayClient()
    svc = MetricIngestService(fake, max_bulk_items=10)  # type: ignore[arg-type]
    await svc.delete(job="myjob")
    assert fake.deleted == [("myjob", {})]
