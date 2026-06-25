# Access Review Service

## Purpose

The Access Review service periodically verifies that users still require the permissions and access levels they currently possess.

The goal is to ensure that access remains appropriate over time and that unnecessary or excessive permissions are removed.

## Example

Every quarter, managers may receive a list of employees and their assigned access:

```text id="m7k291"
Alice   → Tenant Admin
Bob     → Billing Admin
Charlie → Auditor
```

Managers then review access and decide whether to:

* Approve access
* Revoke access
* Request changes

## Responsibilities

The Access Review service handles:

* Access certification
* Compliance reviews
* Permission recertification
* SOX audit support
* GDPR audit support
* ISO compliance reviews

## Access Review Workflow

```text id="n2f714"
Generate Review
        ↓
Assign Reviewer
        ↓
Review User Access
        ↓
Approve / Revoke Access
        ↓
Complete Review
```

## Ownership Model

An access review owns and manages the following attributes:

```text id="p8x605"
Access Review
├── Reviewer
├── Users
├── Assigned Roles
├── Permissions
├── Review Status
└── Results
```

## Example Structure

Example access review object:

```json id="h4w932"
{
  "id": "review_q2_2026",
  "reviewer_id": "manager_123",
  "review_period": "Q2-2026",
  "status": "in_progress",
  "users": [
    {
      "user_id": "alice",
      "role": "Tenant Admin",
      "decision": "approved"
    }
  ]
}
```

## API Endpoints

### Access Review Management

```http id="v0m347"
POST   /access-reviews
GET    /access-reviews
GET    /access-reviews/{id}
```

### Review Lifecycle

```http id="r6n810"
POST   /access-reviews/{id}/start
POST   /access-reviews/{id}/complete
```

### Review Actions

```http id="d2q549"
POST   /access-reviews/{id}/approve
POST   /access-reviews/{id}/revoke
```

### Review Results

```http id="y9f126"
GET    /access-reviews/{id}/results
```

## Access Review Relationships

```text id="g5k420"
Access Review
├── Reviewer
├── Users
│   ├── Roles
│   └── Permissions
├── Decisions
│   ├── Approve
│   └── Revoke
└── Results
```
