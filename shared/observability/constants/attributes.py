"""Semantic attribute key constants for NutraTenant OTel spans and metrics."""

from __future__ import annotations

# OpenTelemetry semantic conventions
SERVICE_NAME = "service.name"
DEPLOYMENT_ENV = "deployment.environment"

# HTTP
HTTP_METHOD = "http.method"
HTTP_ROUTE = "http.route"
HTTP_STATUS_CODE = "http.status_code"
HTTP_URL = "http.url"
HTTP_TARGET = "http.target"

# Database
DB_SYSTEM = "db.system"
DB_OPERATION = "db.operation"
DB_NAME = "db.name"
DB_STATEMENT = "db.statement"

# Cache
CACHE_HIT = "cache.hit"
CACHE_KEY = "cache.key"
CACHE_BACKEND = "cache.backend"

# NutraTenant domain
TENANT_ID = "tenant.id"
REQUEST_ID = "request.id"
USER_ID = "user.id"
LIFECYCLE_STATE = "tenant.lifecycle_state"
ISOLATION_DECISION = "isolation.decision"
