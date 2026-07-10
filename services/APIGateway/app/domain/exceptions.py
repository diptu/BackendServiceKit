"""Domain exceptions for the API Gateway."""

from __future__ import annotations


class RouteNotFoundError(Exception):
    """No registered route matches the requested path."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"No upstream route found for path: {path!r}")


class UpstreamTimeoutError(Exception):
    """Upstream service did not respond within the configured timeout."""

    def __init__(self, upstream: str, timeout: float) -> None:
        self.upstream = upstream
        self.timeout = timeout
        super().__init__(f"Upstream {upstream!r} timed out after {timeout}s")


class UpstreamUnavailableError(Exception):
    """Upstream service is unreachable (connection refused, DNS failure, etc.)."""

    def __init__(self, upstream: str, detail: str) -> None:
        self.upstream = upstream
        self.detail = detail
        super().__init__(f"Upstream {upstream!r} is unavailable: {detail}")


class GatewayTokenInvalidError(Exception):
    """The Authorization: Bearer access token is missing, expired, or invalid."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Access token is invalid: {reason}.")
