# Tenant Lifecycle

## Tenant Management Service

---

# 1. Overview

This document describes the **end-to-end lifecycle of a Tenant** in the SaaS platform, from initial creation to final deletion.

The lifecycle defines how a tenant is provisioned, activated, maintained, suspended, archived, and eventually removed.

---

# 2. Lifecycle Stages

## High-Level Flow

```text
Create Request
     ↓
Draft
     ↓
Provisioning
     ↓
Active
   ↙       ↘
Suspended   Archived
   ↘          ↓
    Active    Deleted
       ↓
    Deleted
```

---

# 3. Lifecycle Phases

## 3.1 Tenant Creation Phase

### Trigger

`POST /tenants`

### Description

A tenant record is created in a minimal state.

### System Actions

* Validate input
* Generate tenant ID
* Store base tenant record
* Set `state = Draft`
* Emit `TenantCreated`

### Outcome

Tenant exists but is not usable.

---

## 3.2 Provisioning Phase

### Trigger

Automatic system workflow after creation

### Description

All required platform resources are prepared for the tenant.

### System Actions

* Initialize IAM context
* Create default configuration
* Allocate database schema or partition
* Initialize tenant settings
* Register tenant in service registry
* Apply default policies
* Set up audit tracking

### Events

* `TenantProvisioningStarted`
* `TenantProvisioningCompleted`
* `TenantProvisioningFailed`

### Outcome

Tenant becomes ready for activation.

---

## 3.3 Activation Phase

### Trigger

* Provisioning success
* Admin approval
* Subscription activation

### Description

Tenant becomes fully operational.

### System Actions

* Enable authentication
* Enable API access
* Enable user onboarding
* Activate organizations
* Enable billing hooks
* Enable feature flags

### Events

* `TenantActivated`

### Outcome

Tenant is fully usable.

---

## 3.4 Active Usage Phase

### Description

This is the steady-state phase of the tenant.

### Responsibilities

* User operations
* Organization management
* Resource usage
* Billing tracking
* Feature usage
* Policy enforcement

### System Behavior

* All APIs fully enabled
* Full read/write access
* Real-time event processing enabled

---

## 3.5 Suspension Phase

### Trigger

* Billing failure
* Admin action
* Policy violation
* Security incident

### Description

Temporary disablement of tenant operations.

### System Actions

* Disable login
* Disable API access
* Freeze write operations
* Retain all data
* Keep audit logging active

### Events

* `TenantSuspended`

### Outcome

Tenant is inactive but recoverable.

---

## 3.6 Reactivation Phase

### Trigger

* Payment recovery
* Admin approval
* Policy resolution

### Description

Suspended tenant is restored to active state.

### System Actions

* Restore API access
* Restore authentication
* Re-enable services
* Validate subscription state

### Events

* `TenantReactivated`

### Outcome

Tenant resumes normal operation.

---

## 3.7 Archival Phase

### Trigger

* Long inactivity
* Compliance requirement
* Admin decision

### Description

Tenant is moved into long-term retention mode.

### System Actions

* Make tenant read-only
* Disable writes permanently
* Freeze configuration changes
* Retain audit history
* Reduce resource allocation

### Events

* `TenantArchived`

### Outcome

Tenant becomes immutable and compliance-ready.

---

## 3.8 Deletion Phase

### Trigger

* Admin request
* Retention policy expiration
* Compliance purge request

### Description

Final lifecycle stage where tenant is removed or soft-deleted.

### System Actions

* Revoke all access tokens
* Delete tenant metadata (soft/hard)
* Trigger cleanup in dependent services
* Remove resource allocations
* Purge or archive logs based on policy

### Events

* `TenantDeleted`

### Outcome

Tenant is no longer accessible.

---

# 4. Lifecycle Actors

## 4.1 System Actor

Responsible for:

* Provisioning
* Event handling
* State transitions
* Background jobs

---

## 4.2 Platform Admin

Responsible for:

* Tenant creation
* Suspension
* Archival
* Deletion
* Recovery actions

---

## 4.3 Billing System

Responsible for:

* Activation triggers
* Suspension triggers
* Reactivation triggers

---

## 4.4 Compliance System

Responsible for:

* Archival triggers
* Deletion requests
* Retention enforcement

---

# 5. Lifecycle Rules

## LR-001 Sequential Flow

A tenant must follow the defined lifecycle order.

Skipping states is not allowed.

---

## LR-002 Terminal State

`Deleted` is a terminal state.

No transitions are allowed after deletion.

---

## LR-003 Recovery Rules

Only these recoveries are allowed:

* `Suspended → Active`
* `Archived → Deleted` (only via admin or policy)

---

## LR-004 Idempotency

Repeated lifecycle actions must not cause inconsistent state.

---

## LR-005 Event Consistency

Every lifecycle transition must emit a corresponding domain event.

---

## LR-006 Audit Requirement

Every transition must be logged in the audit system with:

* Actor
* Timestamp
* Previous state
* New state
* Reason

---

# 6. Lifecycle Dependencies

Tenant lifecycle depends on:

* IAM Service
* Subscription Service
* Billing Service
* Organization Service
* Notification Service
* Audit Logging Service
* Event Bus Service

---

# 7. Failure Handling

## 7.1 Provisioning Failure

* Retry automatically
* Mark tenant as `ProvisioningFailed`
* Notify admin

---

## 7.2 Activation Failure

* Roll back to `Provisioning` or `Suspended`
* Log failure event

---

## 7.3 Deletion Failure

* Queue for retry
* Ensure eventual consistency cleanup

---

# 8. Lifecycle Metrics

Track:

* Time to Provision
* Time to Activate
* Suspension Rate
* Reactivation Rate
* Deletion Rate
* Failed Provisioning Count

---

# 9. Summary

The Tenant Lifecycle ensures:

* Controlled tenant evolution
* Strong consistency
* Enterprise-grade governance
* Full auditability
* Safe multi-tenant isolation
