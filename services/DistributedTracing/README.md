Distributed Tracing Service
Responsibility

Tracks one request across every microservice.

Example Flow

User Login

Gateway
    ↓
IAM
    ↓
Policy
    ↓
Tenant
    ↓
Notification

Instead of separate logs, you get a complete request journey:

Request
    ↓
Gateway
    ↓
IAM
    ↓
Policy
    ↓
Notification
    ↓
Response

Every request contains:

Trace ID
Span ID
Parent Span

Very useful for debugging and understanding request flow across distributed systems.

Typical APIs
Method	Endpoint
GET	/traces
GET	/traces/{trace_id}
GET	/traces/{trace_id}/timeline
GET	/traces/{trace_id}/spans
GET	/traces/search
POST	/traces/export
GET	/traces/service/{service}
GET	/traces/errors
GET	/traces/slow
DELETE	/traces/{trace_id}
Example Response
{
  "trace_id": "trc_7d91ab",
  "span_id": "spn_203",
  "parent_span": "spn_101",
  "service": "iam",
  "operation": "validate-user",
  "duration_ms": 45,
  "status": "success"
}