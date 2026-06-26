# Alerting Service

## Responsibility

Generates alerts when monitoring detects problems.

### Examples

- CPU > 90%
- Memory > 95%
- Database Down
- Policy Engine Failed
- Payment Failure Rate High
- Queue Full
- Unauthorized Access Spike

It can send notifications through:

- Email
- SMS
- Slack
- Teams
- PagerDuty
- Webhooks

---

## Typical APIs

| Method | Endpoint |
|----------|-----------|
| POST | `/alerts` |
| GET | `/alerts` |
| GET | `/alerts/{id}` |
| PATCH | `/alerts/{id}/acknowledge` |
| PATCH | `/alerts/{id}/resolve` |
| GET | `/alerts/rules` |
| POST | `/alerts/rules` |
| PUT | `/alerts/rules/{id}` |
| DELETE | `/alerts/rules/{id}` |
| POST | `/alerts/test` |

---

## Example Response

```json
{
  "id": "alt_1001",
  "severity": "critical",
  "service": "database",
  "message": "Database connection unavailable",
  "status": "active",
  "created_at": "2026-06-26T10:15:00Z"
}