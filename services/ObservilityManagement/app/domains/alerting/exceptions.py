"""Alerting-domain-specific exceptions."""

from __future__ import annotations


class AlertmanagerUnavailableError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Alertmanager is unavailable: {detail}")
        self.detail = detail


class AlertmanagerError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Alertmanager request failed ({status_code}): {detail}")
        self.status_code = status_code
        self.detail = detail


class AlertNotFoundError(Exception):
    pass


class PrometheusUnavailableError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Prometheus is unavailable: {detail}")
        self.detail = detail


class PrometheusError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Prometheus request failed ({status_code}): {detail}")
        self.status_code = status_code
        self.detail = detail


class RuleNotFoundError(Exception):
    pass


class RuleAlreadyExistsError(Exception):
    pass


class RuleNotManagedError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Rule {name!r} is defined in a static alert file, not managed by this "
            "domain — edit its YAML file directly and reload Prometheus."
        )
        self.name = name
