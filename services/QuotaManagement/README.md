# Quota Management Service

## Responsibility

The Quota Management Service enforces resource limits and access restrictions based on tenant plans and configured policies.

The service consumes usage information from the Usage Metering Service and determines whether operations are permitted.

It answers questions such as:

* Has a tenant exceeded its plan limit?
* Can a user create another workspace?
* Can a tenant upload more files?
* Can a tenant consume additional resources?

The service does **not**:

* Record usage events
* Calculate billing amounts
* Collect payments
* Generate invoices

---

## Dependencies

Consumes:

* Usage Metering Service

Provides:

* Quota validation
* Limit enforcement
* Violation tracking

---

## Example

### Plan Configuration

```json
{
  "users": 100,
  "storage_gb": 50,
  "api_requests": 100000
}
```

### Current Usage

```json
{
  "users": 99,
  "storage_gb": 48
}
```

The Quota Management Service determines whether the next operation is allowed.

---

## Core Concepts

### Quota

Represents a limit applied to a measurable resource.

Examples:

* Maximum users
* Maximum storage
* Maximum API requests

Attributes:

| Field    | Type   | Description           |
| -------- | ------ | --------------------- |
| id       | UUID   | Quota identifier      |
| resource | String | Resource name         |
| limit    | Number | Maximum allowed value |
| unit     | String | Measurement unit      |

---

### QuotaRule

Defines enforcement logic for quotas.

Examples:

* Hard limit
* Soft limit
* Warning threshold

Attributes:

| Field     | Type   | Description     |
| --------- | ------ | --------------- |
| id        | UUID   | Rule identifier |
| quota_id  | UUID   | Related quota   |
| type      | String | Rule type       |
| threshold | Number | Threshold value |

---

### QuotaAssignment

Associates quotas with specific tenants or plans.

Attributes:

| Field     | Type   | Description           |
| --------- | ------ | --------------------- |
| id        | UUID   | Assignment identifier |
| tenant_id | String | Tenant identifier     |
| quota_id  | UUID   | Assigned quota        |

---

### QuotaViolation

Records attempts to exceed configured limits.

Attributes:

| Field     | Type     | Description          |
| --------- | -------- | -------------------- |
| id        | UUID     | Violation identifier |
| tenant_id | String   | Tenant identifier    |
| resource  | String   | Resource exceeded    |
| requested | Number   | Requested amount     |
| timestamp | DateTime | Event time           |

---

## Database Entities

* Quota
* QuotaRule
* QuotaAssignment
* QuotaViolation

---

## API Endpoints

### Quotas

| Method | Endpoint              | Description                |
| ------ | --------------------- | -------------------------- |
| GET    | `/quotas`             | Retrieve all quotas        |
| POST   | `/quotas`             | Create a quota             |
| PUT    | `/quotas/{id}`        | Update quota configuration |
| GET    | `/quotas/{tenant_id}` | Retrieve tenant quotas     |

---

### Quota Operations

| Method | Endpoint           | Description                 |
| ------ | ------------------ | --------------------------- |
| POST   | `/quotas/check`    | Validate quota availability |
| POST   | `/quotas/increase` | Increase quota allocation   |
| POST   | `/quotas/decrease` | Reduce quota allocation     |

---

### Violations

| Method | Endpoint            | Description               |
| ------ | ------------------- | ------------------------- |
| GET    | `/quota-violations` | Retrieve quota violations |

---

## Example Request

### POST /quotas/check

```json
{
  "tenant_id": "tenant_123",
  "resource": "users",
  "requested": 1
}
```

### Response

```json
{
  "allowed": true
}
```

---

## Typical Flow

1. Client requests an operation.
2. Service retrieves current usage.
3. Service retrieves assigned quotas.
4. Rules are evaluated.
5. Operation is either allowed or rejected.
6. Violations are recorded if limits are exceeded.

---

## Notes

* Quota checks should be fast and highly available.
* Support both hard and soft limits.
* Quotas should support dynamic updates.
* Cache frequently used quota configurations.
* Validation should be idempotent where possible.
