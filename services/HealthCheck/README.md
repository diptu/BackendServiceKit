# HealthCheck Service

## Responsibility

Every microservice exposes health endpoints so load balancers, Kubernetes, and monitoring systems know whether it is safe to send traffic.

Health checks are lightweight and should not perform expensive operations.

### Common Checks

- Process is running
- Database connectivity
- Cache connectivity
- Message broker connectivity
- External dependency availability

Many platforms distinguish between:

### Health Check Types

**Liveness**
> Is the process alive?

**Readiness**
> Can it serve requests?

**Startup**
> Has initialization completed?

---

## Typical APIs

| Method | Endpoint |
|----------|-----------|
| GET | `/health` |
| GET | `/health/live` |
| GET | `/health/ready` |
| GET | `/health/startup` |
| GET | `/health/dependencies` |
| GET | `/health/database` |
| GET | `/health/cache` |
| GET | `/health/message-broker` |
| GET | `/health/details` |
| GET | `/health/version` |

---

## Example Response

```json
{
    "status": "healthy",
    "database": "up",
    "redis": "up",
    "message_broker": "up",
    "uptime": "14d 08h"
}

```text
Application
      │
      ├──────────────► Logging Service
      │
      ├──────────────► Metrics Collection Service
      │
      ├──────────────► Distributed Tracing Service
      │
      └──────────────► Health Check Service
                           │
                           ▼
                  Monitoring Service
                           │
                    Threshold Evaluation
                           │
                           ▼
                   Alerting Service
                           │
                Email / Slack / SMS / Teams
                           │
                           ▼
                  Observability Service
      (Unified Logs + Metrics + Traces + Health)
```