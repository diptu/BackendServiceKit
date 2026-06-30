---
name: multi-service-observability-full-stack
description: >
  Production-grade observability architecture for distributed microservices using
  Kong Gateway, FastAPI, OpenTelemetry, OpenTelemetry Collector, Prometheus,
  Grafana, and Tempo/Jaeger. Implements zero-code instrumentation,
  distributed tracing, metrics collection, log correlation, and
  enterprise-grade monitoring best practices.
---

# Multi-Service Observability (Full Stack)
- **Execution**: Run `/trace <service_name>`.
## Purpose

This skill defines the standard observability architecture for all microservices.

It ensures every service automatically emits:

- 📈 Metrics
- 🔍 Distributed Traces
- 📜 Structured Logs
- 🚨 Alerting Signals

without polluting business logic.

The architecture follows the OpenTelemetry ecosystem and is designed for cloud-native production environments.

---

# Architecture

```text
                    Client
                       │
                       ▼
               Kong API Gateway
             (traceparent injection)
                       │
      ─────────────────┼─────────────────
                       │
          FastAPI / Python Services
        (Auto Instrumentation Only)
                       │
               OTLP (gRPC/HTTP)
                       │
                       ▼
          OpenTelemetry Collector
        ┌──────────┬──────────────┐
        │          │              │
        ▼          ▼              ▼
   Prometheus    Tempo         Logging Backend
    Metrics      Traces        (Loki / ELK)

        │          │
        └────┬─────┘
             ▼
          Grafana
```

---

# Core Principles

## 1. Zero-Code Instrumentation

Business logic must never contain telemetry code.

Use runtime auto instrumentation.

Preferred:

```bash
opentelemetry-instrument uvicorn main:app
```

Avoid manually creating spans unless absolutely necessary.

---

## 2. Collector-First Architecture

Applications never communicate directly with:

- Prometheus
- Tempo
- Jaeger
- Grafana

Everything flows through a centralized OpenTelemetry Collector.

```text
Application

↓

OTel Collector

↓

Backends
```

Benefits

- Central configuration
- Security
- Data transformation
- Sampling
- PII masking
- Vendor independence

---

## 3. W3C Trace Context

Every request must carry

```
traceparent
```

and optionally

```
tracestate
```

Kong is responsible for creating the trace when missing.

Every downstream service propagates the same context.

---

## 4. Correlation Everywhere

Every log entry should include

- trace_id
- span_id
- service.name
- deployment.environment

This enables:

Dashboard

↓

Metric spike

↓

Trace

↓

Log

↓

Root cause

---

## 5. OpenTelemetry Standards

Only use OpenTelemetry protocols.

Preferred transport:

- OTLP gRPC
- OTLP HTTP

Avoid vendor-specific SDKs.

---

# Technology Stack

| Component | Responsibility |
|------------|---------------|
| Kong | Trace generation & propagation |
| FastAPI | Application |
| OpenTelemetry SDK | Telemetry generation |
| OpenTelemetry Collector | Processing & exporting |
| Prometheus | Metrics |
| Tempo / Jaeger | Distributed tracing |
| Loki / ELK | Logging |
| Grafana | Visualization |
| Alertmanager | Alerts |

---

# OpenTelemetry Collector

## Reference Configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s

  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: myapp

  otlp:
    endpoint: tempo:4317
    tls:
      insecure: true

service:
  pipelines:

    metrics:
      receivers: [otlp]
      processors: [batch, memory_limiter]
      exporters: [prometheus]

    traces:
      receivers: [otlp]
      processors: [batch, memory_limiter]
      exporters: [otlp]
```

---

# Kong Gateway

## Responsibilities

- Generate traceparent
- Continue existing traces
- Propagate headers
- Export traces

Recommended plugin

```
opentelemetry
```

Responsibilities

- Root span creation
- HTTP timing
- Context propagation
- Error tagging

---

# FastAPI Services

## Runtime Instrumentation

Never modify application code.

Launch using

```bash
export OTEL_SERVICE_NAME=user-service

export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

opentelemetry-instrument \
uvicorn app.main:app
```

---

## Automatic Instrumentation

Enable

- FastAPI
- ASGI
- HTTPX
- Requests
- SQLAlchemy
- Psycopg
- Redis
- Celery

This provides automatic

- HTTP spans
- Database spans
- Cache spans
- Outgoing request spans

---

# Metrics

Recommended RED metrics

- Request rate
- Error rate
- Duration

Recommended USE metrics

- CPU
- Memory
- Network
- Disk

Business metrics

- Login count
- Registration count
- Active users
- API usage
- Queue length

---

# Tracing

Every request should produce spans similar to

```text
Gateway

↓

Authentication

↓

Authorization

↓

Business Logic

↓

Database

↓

Redis

↓

External API
```

Every span should include

- service.name
- operation
- duration
- status
- http.route
- http.method

---

# Logging

Use structured JSON logs.

Example

```json
{
  "timestamp":"...",
  "service":"user-service",
  "trace_id":"...",
  "span_id":"...",
  "level":"INFO",
  "message":"User authenticated"
}
```

Never use plain text logs in production.

---

# Security

The collector must remove

- Authorization
- Cookie
- Set-Cookie
- JWT
- API Keys
- Passwords
- Tokens

using transform processors before exporting.

Never export PII.

---

# Grafana

## Data Sources

- Prometheus
- Tempo
- Loki

Recommended dashboards

- Service Overview
- API Latency
- Error Rate
- Infrastructure
- Database
- Kubernetes
- Queue Workers

Enable Trace ↔ Log ↔ Metric correlation.

---

# Alerting

Create alerts for

- High latency
- High error rate
- Pod restarts
- Memory exhaustion
- CPU saturation
- Database failures
- Queue backlog

Use Prometheus Alertmanager.

---

# Verification Checklist

## Gateway

- traceparent exists
- spans exported

---

## Service

- metrics generated
- traces generated
- logs include trace_id

---

## Collector

- receiving OTLP
- exporting metrics
- exporting traces
- no dropped telemetry

---

## Prometheus

Verify

```
http://otel-collector:8889/metrics
```

is reachable.

---

## Tempo

Confirm

- spans visible
- parent-child relationships correct
- latency waterfall present

---

## Grafana

Verify

- dashboards populate
- traces open from metrics
- logs link to traces

---

# Best Practices

- Never instrument business logic manually unless necessary.
- Use automatic instrumentation wherever possible.
- Always propagate W3C Trace Context.
- Centralize telemetry through the OpenTelemetry Collector.
- Mask sensitive data before export.
- Use structured JSON logging.
- Prefer OTLP over vendor-specific protocols.
- Keep dashboards reusable across all services.
- Correlate logs, metrics, and traces using `trace_id`.
- Monitor the observability stack itself (Collector, Prometheus, Tempo, Grafana).

---

# Expected Outcome

Following this standard provides:

- Consistent telemetry across every microservice
- Minimal instrumentation effort
- End-to-end distributed tracing
- Unified metrics collection
- Centralized logging
- Production-grade monitoring
- Faster incident response
- Easier root cause analysis
- Vendor-neutral observability architecture
- Cloud-native scalability
