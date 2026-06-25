# Access Request Service

## Purpose

The Access Request service enables users to request permissions or roles that they do not currently possess.

Requests are submitted into an approval workflow where reviewers determine whether access should be granted.

## Example

A developer may request additional access:

```text id="f3n920"
Developer Request

Tenant:
    Acme Corp

Access:
    Billing Admin
```

The request is then submitted into an approval process.

## Responsibilities

The Access Request service handles:

* Create access requests
* Track request status
* Cancel requests
* Submit requests for approval
* View request history

## Access Request Workflow

```text id="r4k173"
Create Request
        ↓
Submit Request
        ↓
Approval Workflow
        ↓
Approve / Reject
        ↓
Assign Access
```

## Ownership Model

An access request owns and manages the following attributes:

```text id="j7m512"
Access Request
├── Requester
├── Target Entity
├── Requested Role
├── Status
├── Reason
└── Metadata
```

## Example Structure

Example access request object:

```json id="v2d846"
{
  "requester_id": "user_123",
  "entity_type": "tenant",
  "entity_id": "tenant_456",
  "requested_role": "Billing Admin",
  "reason": "Need access to manage invoices",
  "status": "pending"
}
```

## API Endpoints

### Request Management

```http id="g6z301"
POST   /access-requests
GET    /access-requests
GET    /access-requests/{id}
```

### Request Actions

```http id="s8q725"
POST   /access-requests/{id}/cancel
POST   /access-requests/{id}/submit
```

### User Requests

```http id="p5r904"
GET    /access-requests/my
```

## Access Request Relationships

```text id="t1x693"
Access Request
├── Requester
├── Target Entity
├── Requested Role
├── Approval Workflow
├── Status
└── Result
```
