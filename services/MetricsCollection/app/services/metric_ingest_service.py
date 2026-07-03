"""Push/delete escape hatch — see TODO.md Decision #4.

For short-lived/batch processes that can't be scraped (e.g. Celery
workers). Long-running FastAPI services are already scraped directly by
Prometheus with zero code here — this path is not for them.

Pushed metrics land in Pushgateway, a *separate* store from Prometheus's own
scraped series (Decision #4) — grouped only by `job` in the Pushgateway URL;
any other caller-supplied `labels` are ordinary metric labels in the
exposition text body, not part of the grouping key.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.domain.exceptions import BulkPushLimitExceededError
from app.infrastructure.pushgateway.pushgateway_client import PushgatewayClient
from app.schemas.metric import MetricPushCreate

logger = logging.getLogger(__name__)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _build_exposition_text(items: list[MetricPushCreate]) -> str:
    lines: list[str] = []
    declared_types: set[str] = set()
    for item in items:
        if item.metric not in declared_types:
            lines.append(f"# TYPE {item.metric} {item.metric_type}")
            declared_types.add(item.metric)
        if item.labels:
            label_str = ",".join(f'{k}="{_escape(v)}"' for k, v in item.labels.items())
            lines.append(f"{item.metric}{{{label_str}}} {item.value}")
        else:
            lines.append(f"{item.metric} {item.value}")
    return "\n".join(lines) + "\n"


class MetricIngestService:
    def __init__(self, pushgateway_client: PushgatewayClient, *, max_bulk_items: int) -> None:
        self._pg = pushgateway_client
        self._max_bulk_items = max_bulk_items

    async def push_one(self, item: MetricPushCreate) -> int:
        return await self.push_bulk([item])

    async def push_bulk(self, items: list[MetricPushCreate]) -> int:
        if len(items) > self._max_bulk_items:
            raise BulkPushLimitExceededError(len(items), self._max_bulk_items)

        groups: dict[str, list[MetricPushCreate]] = defaultdict(list)
        for item in items:
            groups[item.job].append(item)

        for job, group_items in groups.items():
            text = _build_exposition_text(group_items)
            await self._pg.push(job=job, labels={}, exposition_text=text)

        logger.info("metrics_pushed", extra={"count": len(items), "jobs": list(groups.keys())})
        return len(items)

    async def delete(self, *, job: str) -> None:
        await self._pg.delete(job=job, labels={})
        logger.info("metrics_deleted", extra={"job": job})
