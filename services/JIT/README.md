# Just-In-Time (JIT) Access Service

## Purpose

The Just-In-Time (JIT) Access service grants temporary access only when it is needed.

Instead of assigning standing privileges permanently, users receive time-limited access that automatically expires and is revoked after the approved duration.

## Example

An engineer requires temporary production access:

```text id="q2v681"
Request:

Need DB access for 1 hour
```

The system grants:

```text id="r5f913"
Granted Access:

Database Admin
Expires in: 1 hour
```

Once the expiration period is reached:

```text id="w1m346"
Access automatically revoked
```

## Responsibilities

The JIT Access service handles:

* Temporary privilege elevation
* Time-bound permissions
* Automatic access revocation
* Active session tracking
* Expiration management

## JIT Access Workflow

```text id="t8n720"
Request Temporary Access
            ↓
Approval Process
            ↓
Grant Temporary Role
            ↓
Access Active
            ↓
Automatic Expiration
            ↓
Revoke Access
```

## Ownership Model

A JIT access request owns and manages the following attributes:

```text id="h3p812"
JIT Access
├── Requester
├── Target Resource
├── Temporary Role
├── Duration
├── Status
└── Expiration
```

## Example Structure

Example JIT request object:

```json id="m9x214"
{
  "requester_id": "user_123",
  "resource": "production_database",
  "role": "Database Admin",
  "duration": "1h",
  "status": "active",
  "expires_at": "2026-06-25T16:00:00Z"
}
```

## API Endpoints

### JIT Request Management

```http id="b7q931"
POST   /jit-requests
GET    /jit-requests
GET    /jit-requests/{id}
```

### Approval Actions

```http id="f2r574"
POST   /jit-requests/{id}/approve
POST   /jit-requests/{id}/deny
```

### Active Access Management

```http id="n5z180"
GET    /jit-access/active
POST   /jit-access/revoke
```

## JIT Relationships

```text id="d6u407"
JIT Access
├── Requester
├── Target Resource
├── Temporary Role
├── Duration
├── Active Session
└── Expiration
```
