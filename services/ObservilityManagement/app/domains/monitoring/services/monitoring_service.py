"""Cross-service aggregation for the Monitoring domain.

Every public method composes other domains'/services' already-existing
APIs and degrades independently: one unreachable source marks only itself
unreachable, never fails the whole call. Alert count is fetched by calling
the Alerting domain's own service class directly (in-process — this
merge's Decision #4 applies within tier-3, not just for Observability):
no separate Alertmanager connection is needed here since Alerting already
maintains one.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app.domains.monitoring.infrastructure.gateway_client import GatewayClient
from app.domains.monitoring.infrastructure.tenent_client import TenentClient
from app.domains.monitoring.repositories.monitoring_repository import (
    ClusterInfo,
    PlatformStatus,
    ResourceHealth,
    ServiceHealth,
    TenantSummary,
    extract_dependency,
    first_non_none,
    overall_status,
    services_from_gateway_status,
)

if TYPE_CHECKING:
    from app.domains.alerting.services.alert_service import AlertService


class MonitoringService:
    def __init__(
        self,
        gateway_client: GatewayClient,
        tenent_client: TenentClient,
        alert_service: "AlertService",
    ) -> None:
        self._gateway = gateway_client
        self._tenent = tenent_client
        self._alerts = alert_service

    async def get_services(self) -> list[ServiceHealth]:
        gateway_status = await self._gateway.get_gateway_status()
        return services_from_gateway_status(gateway_status)

    async def get_status(self) -> PlatformStatus:
        services, alerts = await asyncio.gather(self.get_services(), self._safe_list_alerts())
        active_alert_count = (
            sum(1 for a in alerts if a.state == "active") if alerts is not None else None
        )
        return PlatformStatus(
            overall_status=overall_status(services),
            services=services,
            active_alert_count=active_alert_count,
        )

    async def get_service_detail(self, service_id: str) -> ServiceHealth | None:
        for svc in await self.get_services():
            if svc.name == service_id:
                return svc
        return None

    async def get_resources(self) -> ResourceHealth:
        tenent_ready, gateway_status = await asyncio.gather(
            self._tenent.get_ready(), self._gateway.get_gateway_status()
        )
        postgres = extract_dependency(tenent_ready, "postgres")
        redis = first_non_none(
            extract_dependency(tenent_ready, "redis"),
            gateway_status.get("redis_connected") if gateway_status else None,
        )
        rabbitmq = gateway_status.get("rabbitmq_connected") if gateway_status else None
        return ResourceHealth(
            postgres_reachable=postgres, redis_reachable=redis, rabbitmq_reachable=rabbitmq
        )

    async def get_tenants(self) -> TenantSummary:
        data = await self._tenent.list_tenants()
        if not data:
            return TenantSummary(total=0, by_status={})
        items = data.get("items", []) if isinstance(data, dict) else []
        by_status: dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "unknown"))
            by_status[status] = by_status.get(status, 0) + 1
        total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
        return TenantSummary(total=total, by_status=by_status)

    def get_clusters(self) -> list[ClusterInfo]:
        return [ClusterInfo(name="default", environment="docker-compose", service_count=1)]

    async def get_summary(self) -> dict[str, Any]:
        status = await self.get_status()
        tenants = await self.get_tenants()
        healthy = sum(1 for s in status.services if s.reachable)
        return {
            "overall_status": status.overall_status,
            "services_healthy": healthy,
            "services_total": len(status.services),
            "tenants_total": tenants.total,
            "active_alert_count": status.active_alert_count,
        }

    async def _safe_list_alerts(self) -> list[Any] | None:
        """Wraps the in-process cross-domain call into Alerting — TODO.md
        Decision #4's "wrap every cross-domain call" rule. `AlertService.list_alerts()`
        deliberately lets AlertmanagerUnavailableError/AlertmanagerError
        propagate for its *own* API consumers; here, as a different
        domain's caller, a dead Alertmanager should degrade this field to
        None, not fail the whole `/monitoring/status` response."""
        try:
            return await self._alerts.list_alerts()
        except Exception:
            return None
