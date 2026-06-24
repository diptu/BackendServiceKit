# Tenant Lifecycle Management Service

## Purpose

Handles the state transitions of a tenant throughout its lifecycle.

## Responsibilities

- Activate tenant
- Suspend tenant
- Lock tenant
- Archive tenant
- Reactivate tenant
- Delete tenant
- Offboard tenant
- Handle subscription expiration

## Owns

- **Tenant status transitions**
- Does **not** own tenant business data

## Tenant State Machine

```text
Pending
   |
   v
Active
   |
   +----> Suspended
   |
   +----> Locked
   |
   +----> Archived
   |
   +----> Deleted
```

## API Endpoints

| Method | Endpoint |
|----------|----------|
| POST | `/tenant-lifecycle/{tenant_id}/activate` |
| POST | `/tenant-lifecycle/{tenant_id}/suspend` |
| POST | `/tenant-lifecycle/{tenant_id}/lock` |
| POST | `/tenant-lifecycle/{tenant_id}/archive` |
| POST | `/tenant-lifecycle/{tenant_id}/reactivate` |
| POST | `/tenant-lifecycle/{tenant_id}/delete` |
| GET | `/tenant-lifecycle/{tenant_id}/history` |

## Example Events

```json
[
  {
    "event": "subscription.expired",
    "tenant_id": "tenant_123"
  },
  {
    "event": "payment.failed",
    "tenant_id": "tenant_123"
  },
  {
    "event": "tenant.archived",
    "tenant_id": "tenant_123"
  },
  {
    "event": "tenant.deleted",
    "tenant_id": "tenant_123"
  }
]
```

## Behavior

The Tenant Lifecycle Management Service listens to business and billing events and performs the appropriate tenant state transition while maintaining lifecycle history.