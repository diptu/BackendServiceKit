# Delegated Administration Service

## Purpose

The Delegated Administration service allows privileged administrators to delegate administrative responsibilities to other users without transferring full ownership.

Delegation enables controlled distribution of administrative tasks while maintaining governance boundaries.

## Example

A Super Admin may delegate specific responsibilities:

```text id="k4r102"
Super Admin
    │
    └── Tenant Admin
            ├── User Management
            ├── Billing
            └── Support
```

Instead of granting unrestricted access, only selected areas of responsibility are delegated.

## Responsibilities

The Delegated Administration service handles:

* Delegate authority
* Scope administrative permissions
* Temporary administration
* Time-based delegation
* Delegation lifecycle management

## Delegation Workflow

```text id="x7n653"
Create Delegation
        ↓
Assign Administrative Scope
        ↓
Activate Delegation
        ↓
Perform Administrative Actions
        ↓
Revoke / Expire Delegation
```

## Ownership Model

A delegation owns and manages the following attributes:

```text id="w9f208"
Delegation
├── Delegator
├── Delegate User
├── Scope
├── Status
├── Start Time
└── Expiration
```

## Example Structure

Example delegation object:

```json id="t5v841"
{
  "delegator_id": "super_admin_123",
  "delegate_user_id": "tenant_admin_456",
  "scope": [
    "user_management",
    "billing",
    "support"
  ],
  "status": "active",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

## API Endpoints

### Delegation Management

```http id="n2g491"
POST   /delegations
GET    /delegations
GET    /delegations/{id}
```

### Delegation Actions

```http id="d8m630"
POST   /delegations/{id}/activate
POST   /delegations/{id}/revoke
```

### User Delegation Queries

```http id="r3x925"
GET    /users/{id}/delegations
```

## Delegation Relationships

```text id="p1k740"
Delegation
├── Delegator
├── Delegate User
├── Administrative Scope
│   ├── User Management
│   ├── Billing
│   └── Support
├── Status
└── Expiration
```
