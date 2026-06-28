# API Reference

**Base URL:** `http://<host>:8000/api/v1`

All endpoints require `Authorization: Bearer <token>`. All request and response bodies are `application/json`.

---

## Common Response Codes

| Code | Meaning |
|---|---|
| `200 OK` | Successful read or update |
| `201 Created` | Resource successfully created |
| `204 No Content` | Successful deletion (no body) |
| `401 Unauthorized` | Missing or invalid bearer token |
| `403 Forbidden` | Authenticated but insufficient permissions |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Business rule violation (duplicate, invalid state) |
| `422 Unprocessable Entity` | Request body validation failed |
| `423 Locked` | Operation not permitted on an archived resource |

---

## Health

### `GET` `/health` — Liveness probe

Confirms the service process is alive.

Used by the platform orchestrator (Kubernetes) to determine whether to restart
the container. Returns `200 OK` as long as the process can handle requests —
it does **not** check downstream dependencies.

**Success:** `200 OK`

---

### `GET` `/ready` — Readiness probe

Confirms the service is ready to accept traffic.

Checks that all required dependencies (database, message broker) are reachable
before returning `200 OK`. The load balancer uses this to decide whether to route
traffic to this instance.

**Success:** `200 OK`

---

## Tenants

### `POST` `/tenants` — Create tenant

Create a new tenant record in `draft` state.

The provisioning workflow is triggered automatically after creation, which
transitions the tenant through `provisioning` → `active`.

**Constraints:**
- `name` (slug) must be globally unique and URL-safe (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`).
- `name` is immutable after creation.
- Only platform administrators may create tenants.

**Success:** `201 Created`

---

### `GET` `/tenants` — List tenants

Return a cursor-paginated list of tenants.

Supports filtering by `status` and `region`. Soft-deleted tenants
(`status=deleted`) are excluded from results unless explicitly requested.

**Sorting:** `created_at` descending by default.

**Success:** `200 OK`

---

### `GET` `/tenants/{tenant_id}` — Get tenant

Retrieve the full tenant record by UUID.

**Success:** `200 OK`

---

### `PATCH` `/tenants/{tenant_id}` — Update tenant

Partially update mutable tenant fields.

**Immutable fields** (cannot be changed after creation):
- `id`
- `name` (slug)
- `created_at`

All other fields in the request body are optional — only provided fields are updated.
Every update emits a `TenantUpdated` domain event and generates an audit record.

**Success:** `200 OK`

---

### `DELETE` `/tenants/{tenant_id}` — Soft-delete tenant

Soft-delete a tenant.

The tenant must be in `archived` state before deletion. The record is retained
for audit purposes and the `name` slug remains reserved until hard-deletion by the
Tenant Offboarding Service.

Emits a `TenantDeleted` domain event.

> **Note:** Hard deletion is handled by the Tenant Offboarding Service, not this endpoint.

**Success:** `204 No Content`

---

## Tenant Lifecycle

### `POST` `/tenants/{tenant_id}/provision` — Start tenant provisioning

Transition a `draft` tenant to `provisioning` state (infrastructure setup begins).

**Valid source state:** `draft`

Emits a `TenantProvisioningStarted` event.

Returns `409 Conflict` for all other source states.

**Success:** `200 OK`

---

### `POST` `/tenants/{tenant_id}/activate` — Activate or reactivate tenant

Transition a tenant to `active` state.

**Valid source states:** `provisioning`, `suspended`

- `provisioning → active`: Called once provisioning is complete and the tenant is ready for use.
- `suspended → active`: Called by a platform administrator to reactivate a suspended tenant.

Emits `TenantActivated` or `TenantReactivated` event depending on the source state.

Returns `409 Conflict` for all other source states.

**Success:** `200 OK`

---

### `POST` `/tenants/{tenant_id}/suspend` — Suspend tenant

Transition an `active` tenant to `suspended` state.

**Effects:**
- All user logins for the tenant are immediately blocked.
- All API access for the tenant is blocked.
- All tenant data is preserved.

Providing a `reason` is strongly recommended for audit clarity.
Emits a `TenantSuspended` event.

Returns `409 Conflict` if the tenant is not currently in `active` state.

**Success:** `200 OK`

---

### `POST` `/tenants/{tenant_id}/archive` — Archive tenant

Transition a tenant to `archived` (read-only) state.

**Valid source states:** `active`, `suspended`

**Effects:**
- All write operations on the tenant and its resources return `423 Locked`.
- The tenant is retained for compliance and audit purposes.
- Archival is a prerequisite for soft-deletion.

Emits a `TenantArchived` event.

**Success:** `200 OK`

---

## Tenant Settings

### `GET` `/tenants/{tenant_id}/settings` — Get tenant settings

Retrieve all configuration settings for a tenant.

**Success:** `200 OK`

---

### `PATCH` `/tenants/{tenant_id}/settings` — Update tenant settings

Partially update tenant configuration settings.

All fields are optional — only provided fields are updated.
Updates are versioned; all changes generate an audit record and emit a
`TenantConfigurationUpdated` event.

Returns `423 Locked` if the tenant is in `archived` state.

**Success:** `200 OK`

---

## Tenant Owners

### `GET` `/tenants/{tenant_id}/owners` — List tenant owners

Return all active owners and admins of the tenant.

**Success:** `200 OK`

---

### `POST` `/tenants/{tenant_id}/owners` — Add tenant owner

Add a user as an owner or admin of the tenant.

The `user_id` must be a valid user ID from the User Service.
Adding the same user twice returns `409 Conflict`.
Ownership changes are audited and emit a `TenantOwnerAdded` event.

**Success:** `201 Created`

---

### `DELETE` `/tenants/{tenant_id}/owners/{owner_id}` — Remove tenant owner

Remove a user from the tenant's owner list.

Returns `422 Unprocessable Entity` if the user being removed is the last active owner.
Every tenant must retain at least one active owner at all times.

Emits a `TenantOwnerRemoved` event.

**Success:** `204 No Content`

---

## Tenant Metadata

### `GET` `/tenants/{tenant_id}/metadata` — Get tenant metadata

Retrieve all key-value metadata entries for a tenant.

**Success:** `200 OK`

---

### `PATCH` `/tenants/{tenant_id}/metadata` — Update tenant metadata

Upsert metadata key-value pairs for a tenant.

**Behaviour:**
- Existing keys are **overwritten**.
- New keys are **added**.
- No keys are deleted by this operation. To clear a key, set its value to `""`.

Updates generate an audit record. No domain event is emitted for metadata changes.

Returns `423 Locked` if the tenant is in `archived` state.

**Success:** `200 OK`

---
