# Monitoring Service

## Responsibility

Continuously monitors the entire platform.

It collects information from all services and infrastructure to determine:

- Is the service running?
- Is it overloaded?
- Is CPU usage high?
- Is memory exhausted?
- Is response time increasing?
- Are databases reachable?
- Are queues backed up?

It does not store logs.

Instead, it consumes:

- Metrics
- Health checks
- Infrastructure status

Think of it as:

> An overall system monitoring dashboard.

---

## Typical APIs

| Method | Endpoint |
|----------|-----------|
| GET | `/monitoring/dashboard` |
| GET | `/monitoring/services` |
| GET | `/monitoring/services/{service_id}` |
| GET | `/monitoring/status` |
| GET | `/monitoring/system` |
| GET | `/monitoring/tenants` |
| GET | `/monitoring/summary` |
| GET | `/monitoring/resources` |
| GET | `/monitoring/nodes` |
| GET | `/monitoring/clusters` |
| POST | `/monitoring/refresh` |

---

## Example Response

```json
{
    "service": "iam",
    "status": "healthy",
    "cpu": 42,
    "memory": 61,
    "uptime": "28 days"
}