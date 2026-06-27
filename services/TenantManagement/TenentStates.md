# Tenant States
## Tenant Management Service

---

# 1. Overview

This document defines the **lifecycle states of a Tenant** in the SaaS platform.

A tenant represents a customer boundary and transitions through multiple states from creation to deletion. Each state defines what operations are allowed, restricted, or blocked.

---

# 2. Tenant State Model

## State Diagram

```text
                    ┌──────────────┐
                    │    Draft     │
                    └──────┬───────┘
                           │
                           v
                    ┌──────────────┐
                    │ Provisioning │
                    └──────┬───────┘
                           │
                           v
                    ┌──────────────┐
        ┌──────────▶│    Active    │◀──────────┐
        │           └──────┬───────┘           │
        │                  │                   │
        │                  v                   │
        │           ┌──────────────┐          │
        │           │  Suspended   │          │
        │           └──────┬───────┘          │
        │                  │                   │
        │                  v                   │
        │           ┌──────────────┐          │
        │           │   Archived   │          │
        │           └──────┬───────┘          │
        │                  │                   │
        │                  v                   │
        │           ┌──────────────┐          │
        └───────────│   Deleted    │──────────┘
                    └──────────────┘
```

# 3. State Definitions
3.1 Draft
Description

Initial state when tenant creation is started but not fully provisioned.

Characteristics
Not usable
No access to APIs
No users active
Allowed Transitions
→ Provisioning
→ Deleted (rollback)
3.2 Provisioning
Description

System is setting up tenant resources (DB, config, defaults).

Characteristics
Partial availability
Background setup running
Allowed Transitions
→ Active
→ Deleted (failure rollback)
3.3 Active
Description

Fully operational tenant.

Characteristics
Full API access
Users and organizations active
Billing enabled
Resources accessible
Allowed Transitions
→ Suspended
→ Archived
→ Deleted
3.4 Suspended
Description

Temporary disable state.

Characteristics
No login allowed
No API access
Data preserved
Allowed Transitions
→ Active
→ Archived
→ Deleted
3.5 Archived
Description

Read-only state for long-term retention.

Characteristics
No write operations
Read-only access (optional)
Used for compliance
Allowed Transitions
→ Deleted (final cleanup only)
3.6 Deleted
Description

Final state after soft or hard deletion.

Characteristics
No access allowed
Data may be soft-deleted or purged
Retention policies apply
Allowed Transitions
None (terminal state)

# 4. State Transition Rules
TR-001 Valid Transitions Only

The system shall enforce strict state transitions as defined in the state model.

Invalid transitions must be rejected.

TR-002 Idempotent Transitions

State update operations must be idempotent:

Re-suspending a suspended tenant is allowed
Re-activating an active tenant is allowed (no-op)
TR-003 System-Controlled Transitions

Some transitions are system-driven:

Provisioning → Active
Provisioning → Deleted (failure)
Suspended → Archived (policy-driven)
Archived → Deleted (retention policy)
TR-004 Manual Transitions

Admin-controlled transitions:

Active → Suspended
Active → Archived
Suspended → Active
Any → Deleted (admin override)
5. State Access Control Matrix
State	API Access	Login	Writes	Reads
Draft	❌	❌	❌	❌
Provisioning	⚠️ Partial	❌	⚠️	⚠️
Active	✅	✅	✅	✅
Suspended	❌	❌	❌	⚠️
Archived	❌	❌	❌	⚠️
Deleted	❌	❌	❌	❌

# 6. State Entry Rules
6.1 Draft Entry Rules
Created via POST /tenants
Minimal validation required
6.2 Provisioning Entry Rules
System automatically transitions after creation
Required services:
IAM initialization
DB provisioning
default config setup
6.3 Active Entry Rules
All provisioning tasks must be complete
Tenant must pass validation checks
6.4 Suspended Entry Rules
Triggered by admin action or billing failure
Must retain all data
6.5 Archived Entry Rules
Triggered by inactivity or compliance policy
Must freeze all write operations
6.6 Deleted Entry Rules
Must respect retention policy
Must ensure no active dependencies

# 7. State Exit Rules
7.1 Exit from Active
Must revoke sessions
Must disable API keys (optional)
7.2 Exit from Suspended
Must validate subscription or admin approval
7.3 Exit from Archived
Only allowed via delete operation

# 8. Event Emission per State
State Change	Event Name
Draft → Provisioning	TenantProvisioningStarted
Provisioning → Active	TenantActivated
Active → Suspended	TenantSuspended
Suspended → Active	TenantReactivated
Active → Archived	TenantArchived
Any → Deleted	TenantDeleted

# 9. Error States
9.1 Provisioning Failed
Tenant remains in Draft or Provisioning
Retry allowed
Event emitted: TenantProvisioningFailed
9.2 Invalid State Transition
API returns 400 Bad Request
Includes error code: INVALID_TENANT_STATE_TRANSITION

# 10. State Persistence Rules
State must be persisted in tenants.status
State changes must be atomic
State transitions must be logged in audit service

# 11. Summary

The tenant lifecycle is strictly controlled to ensure:

Strong tenant isolation
Predictable lifecycle behavior
Auditability
Compliance readiness
Enterprise-grade reliability