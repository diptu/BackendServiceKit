# Tenant Management Service

The **Tenant Management Service** is the authoritative system of record for all tenant data in the platform. It owns tenant profiles, lifecycle state, configuration settings, ownership, and extensible metadata.

A **tenant** is the top-level isolation boundary — every organization, workspace, resource, and user is scoped to exactly one tenant.

| Property | Value |
|---|---|
| Port | `8000` |
| API prefix | `/api/v1` |
| Auth | Bearer token (JWT) |
| Content-Type | `application/json` |

---

## Navigation

- [Getting Started](getting-started.md) — local setup, Docker, environment variables
- [API Reference](api-reference.md) — complete endpoint documentation
- [Tenant Lifecycle](state-machine.md) — state machine and transition rules

---

## What This Service Does

| Capability | Description |
|---|---|
| Tenant CRUD | Create, read, update, soft-delete tenant records |
| Lifecycle transitions | Drive tenants through `draft → provisioning → active ⇄ suspended → archived → deleted` |
| Settings | Per-tenant timezone, locale, currency, theme, session timeout |
| Ownership | Manage owner and admin contacts; enforce ≥ 1 active owner invariant |
| Metadata | Schema-free key-value pairs for arbitrary tenant attributes |
| Health | `/health` and `/ready` probes for Kubernetes and load balancers |

---

## Quick Example

```bash
# Create a tenant
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "alphabet-corp",
    "display_name": "Alphabet Corporation",
    "owner_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "region": "us-east-1"
  }'

# Activate a provisioned tenant
curl -X POST http://localhost:8000/api/v1/tenants/{tenant_id}/activate \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"reason": "Provisioning complete — all checks passed."}'
```

---

> **Interactive API Docs:** Available at [`/docs`](http://localhost:8000/docs) and [`/redoc`](http://localhost:8000/redoc) in non-production environments.
