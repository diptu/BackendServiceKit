"""Domain enumerations for tenant isolation."""

from __future__ import annotations

from enum import StrEnum


class PolicyType(StrEnum):
    STRICT = "strict"
    PARTNER = "partner"
    INTERNAL = "internal"


class IsolationDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class ResourceType(StrEnum):
    DOCUMENT = "document"
    WORKSPACE = "workspace"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    GROUP = "group"
    ORGANIZATION = "organization"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    BILLING_RECORD = "billing_record"
    AUDIT_LOG = "audit_log"


class AccessAction(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
