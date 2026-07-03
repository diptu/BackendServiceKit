"""Domain exceptions."""

from __future__ import annotations


class PrometheusUnavailableError(Exception):
    """Prometheus did not respond (connection/timeout) — 503."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Prometheus is unavailable: {detail}")
        self.detail = detail


class PrometheusQueryError(Exception):
    """Prometheus responded with a non-2xx status, or reported an error status — 502."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Prometheus query failed: {detail}")
        self.detail = detail


class InvalidPromQLError(Exception):
    """Caller-supplied filters could not be translated into a valid query — 422."""


class PushgatewayUnavailableError(Exception):
    """Pushgateway did not respond (connection/timeout) — 503."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Pushgateway is unavailable: {detail}")
        self.detail = detail


class PushgatewayError(Exception):
    """Pushgateway responded with a non-2xx status — 502."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Pushgateway request failed ({status_code}): {detail}")
        self.status_code = status_code
        self.detail = detail


class ScrapedMetricDeleteNotSupportedError(Exception):
    """A caller asked to delete a scraped (pull-based) series — 409.

    Only Pushgateway-originated (pushed) metrics can be deleted through this
    service — see TODO.md Decision #5.
    """

    def __init__(
        self,
        detail: str = (
            "Only metrics pushed through this service (via Pushgateway) can be "
            "deleted. Prometheus's own scraped series cannot be deleted without "
            "enabling --web.enable-admin-api, which is not enabled here."
        ),
    ) -> None:
        super().__init__(detail)


class NotAnOperatorError(Exception):
    """Caller lacks the platform-admin role required for this operator-only service — 403."""

    def __init__(self, detail: str = "Operator (platform-admin) role required.") -> None:
        super().__init__(detail)


class BulkPushLimitExceededError(Exception):
    """POST /metrics/bulk payload exceeds the configured max item count — 422."""

    def __init__(self, count: int, limit: int) -> None:
        super().__init__(f"Bulk payload has {count} items; limit is {limit}.")
        self.count = count
        self.limit = limit
