Metrics Collection Service
Responsibility

Collects numeric measurements.

Unlike logs, metrics are numbers.

Examples

CPU Usage

Memory

Requests/sec

Latency

Cache Hits

Queue Length

Policy Evaluations/sec

Failed Logins

Payments/minute

Metrics are aggregated.

APIs
POST /metrics

POST /metrics/bulk

GET  /metrics

GET  /metrics/query

GET  /metrics/service/{service}

GET  /metrics/tenant/{tenant}

GET  /metrics/system

GET  /metrics/history

GET  /metrics/top

DELETE /metrics

Example
```json
{
    "metric":"cpu_usage",
    "value":67,
    "timestamp":"..."
}
```