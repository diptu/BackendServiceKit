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
draft (TM)
   |
   v (PUT /provisioning)
provisioning
   |
   v (PUT /pending)
pending
   |
   v (PUT /activate)
active
   |
   +----> suspended  <----> active  (PUT /suspend / PUT /reactivate)
   |           |
   |           +----------> archived -----> deleted
   |
   +----> locked     -----> active  (PUT /lock / PUT /unlock)
   |         |
   |         +------------> archived -----> deleted
   |
   +----> archived -------> deleted  (PUT /archive / PUT /delete)
```

## Lifecycle States

| State | Description | Trigger Example |
|-------|-------------|-----------------|
| **draft** | Initial tenant record created; no resources allocated. | Sales creates a "Meta" record in the admin portal. |
| **provisioning** | Async infrastructure setup in progress (DB sharding, API keys, VPC peering). | Terraform provisions Meta's isolated database schema. |
| **pending** | Provisioning complete; awaiting final confirmation or compliance sign-off. | Meta's IT team verifies their primary IdP integration. |
| **active** | Fully operational and billed; users can log in. | Meta employees begin using the platform. |
| **suspended** | Service paused — non-payment or policy violation; data retained. | Meta misses a payment deadline; access is revoked. |
| **locked** | Preventative security hold; admin-triggered for investigation. | Unusual API traffic from Meta's key — admin investigates. |
| **archived** | Long-term cold storage after contract end; no production access. | Meta ends their contract; data retained for audit. |
| **deleted** | Permanent soft-delete; hard purge handled by the Offboarding Service. | Post-retention period — all Meta rows are purged. |

## API Endpoints

| Method | Endpoint | Transition |
|--------|----------|------------|
| PUT | `/tenant-lifecycle/{tenant_id}/provisioning` | → provisioning |
| PUT | `/tenant-lifecycle/{tenant_id}/pending` | provisioning → pending |
| PUT | `/tenant-lifecycle/{tenant_id}/activate` | pending → active |
| PUT | `/tenant-lifecycle/{tenant_id}/suspend` | active → suspended (idempotent) |
| PUT | `/tenant-lifecycle/{tenant_id}/reactivate` | suspended → active |
| PUT | `/tenant-lifecycle/{tenant_id}/lock` | active → locked |
| PUT | `/tenant-lifecycle/{tenant_id}/unlock` | locked → active |
| PUT | `/tenant-lifecycle/{tenant_id}/archive` | active / suspended / locked → archived |
| PUT | `/tenant-lifecycle/{tenant_id}/delete` | archived → deleted |
| GET | `/tenant-lifecycle/{tenant_id}/history` | — |

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