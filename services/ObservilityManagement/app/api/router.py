"""Top-level API router — mounts all seven merged domains' routers under
their unchanged URL prefixes (TODO.md Decision #1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.health_router import router as health_router
from app.core.config import settings
from app.domains.alerting.router import router as alerting_router
from app.domains.health.router import router as health_domain_router
from app.domains.logging.router import router as logging_router
from app.domains.metrics.router import router as metrics_router
from app.domains.monitoring.router import router as monitoring_router
from app.domains.observability.router import router as observability_router
from app.domains.tracing.router import router as tracing_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(logging_router, prefix=settings.api_v1_prefix)
api_router.include_router(tracing_router, prefix=settings.api_v1_prefix)
api_router.include_router(metrics_router, prefix=settings.api_v1_prefix)
api_router.include_router(monitoring_router, prefix=settings.api_v1_prefix)
api_router.include_router(alerting_router, prefix=settings.api_v1_prefix)
api_router.include_router(health_domain_router, prefix=settings.api_v1_prefix)
api_router.include_router(observability_router, prefix=settings.api_v1_prefix)
