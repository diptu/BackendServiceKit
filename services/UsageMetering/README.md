# Usage Metering Service

## Responsibility

The Usage Metering Service tracks and records customer consumption of billable resources across the platform.

Its primary role is to capture and aggregate usage data for reporting and billing-related workflows.

The service answers questions such as:

* How many API calls were made?
* How many documents were uploaded?
* How many GB were stored?
* How many AI tokens were consumed?
* How many users were active?

The service **does not**:

* Enforce usage limits
* Apply quotas
* Charge customers
* Process billing calculations

---

## Example

### Tenant A Usage

| Metric       | Value |
| ------------ | ----- |
| API Requests | 2,500 |
| Storage Used | 10 GB |
| Active Users | 50    |

The Usage Metering Service simply records and exposes these values.

---

## Core Concepts

### Meter

Represents a measurable unit of consumption.

Examples:

* `api_requests`
* `storage_gb`
* `active_users`
* `documents_uploaded`
* `ai_tokens`

Attributes:

| Field       | Type   | Description                |
| ----------- | ------ | -------------------------- |
| id          | UUID   | Unique meter identifier    |
| name        | String | Metric name                |
| unit        | String | Measurement unit           |
| description | String | Human-readable description |

---

### UsageEvent

Represents a single tracked consumption event.

Attributes:

| Field       | Type     | Description                |
| ----------- | -------- | -------------------------- |
| id          | UUID     | Event identifier           |
| tenant_id   | String   | Customer/tenant identifier |
| metric      | String   | Meter name                 |
| quantity    | Number   | Amount consumed            |
| resource_id | String   | Source resource identifier |
| timestamp   | DateTime | Event creation time        |

---

### AggregatedUsage

Stores precomputed summaries of usage data.

Examples:

* Daily API request totals
* Monthly token consumption
* Weekly active users

Attributes:

| Field          | Type   | Description          |
| -------------- | ------ | -------------------- |
| id             | UUID   | Aggregate identifier |
| tenant_id      | String | Tenant identifier    |
| metric         | String | Metric name          |
| total_quantity | Number | Aggregated value     |
| period_id      | UUID   | Related usage period |

---

### UsagePeriod

Represents a time window used for aggregation and reporting.

Examples:

* Hourly
* Daily
* Monthly
* Billing cycle

Attributes:

| Field      | Type     | Description       |
| ---------- | -------- | ----------------- |
| id         | UUID     | Period identifier |
| start_date | DateTime | Start of period   |
| end_date   | DateTime | End of period     |
| type       | String   | Period type       |

---

## Database Entities

* Meter
* UsageEvent
* AggregatedUsage
* UsagePeriod

---

## API Endpoints

### Usage Events

| Method | Endpoint             | Description                     |
| ------ | -------------------- | ------------------------------- |
| POST   | `/usage/events`      | Record a usage event            |
| GET    | `/usage/events`      | Retrieve usage events           |
| GET    | `/usage/events/{id}` | Retrieve a specific usage event |

---

### Usage Summary

| Method | Endpoint                     | Description                      |
| ------ | ---------------------------- | -------------------------------- |
| GET    | `/usage/summary`             | Retrieve overall usage summary   |
| GET    | `/usage/summary/{tenant_id}` | Retrieve tenant-specific summary |

---

### Metrics

| Method | Endpoint                       | Description             |
| ------ | ------------------------------ | ----------------------- |
| GET    | `/usage/metrics`               | List supported metrics  |
| GET    | `/usage/metrics/{metric_name}` | Retrieve metric details |

---

### Import Operations

| Method | Endpoint        | Description               |
| ------ | --------------- | ------------------------- |
| POST   | `/usage/import` | Bulk import usage records |

---

## Example Usage Event

```json
{
  "tenant_id": "tenant_123",
  "metric": "api_requests",
  "quantity": 1,
  "resource_id": "user-service"
}
```

---

## Typical Flow

1. A system component generates a usage event.
2. The event is sent to `POST /usage/events`.
3. The service stores the event.
4. Aggregation jobs compute summaries.
5. Reporting and billing systems consume aggregated usage data.

---

## Notes

* Usage data should be immutable after recording.
* Aggregations may be generated asynchronously.
* The service should support high event throughput.
* Metrics should remain extensible for future resource types.
* Duplicate event handling and idempotency should be considered.
