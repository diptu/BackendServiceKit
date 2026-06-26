# Security Event Logging Service

## Responsibility

Used by the Security Team.

Focuses on attacks, suspicious behavior, and incident response.

## Examples

- Failed Login
- Brute Force
- Impossible Travel
- Privilege Escalation
- Account Lockout
- Token Replay
- API Abuse
- Rate Limit Hit
- Suspicious IP
- SQL Injection Attempt
- XSS Attempt

These logs usually feed SIEM tools like:

- Splunk
- ELK
- Microsoft Sentinel
- Datadog

## APIs

| Method | Endpoint |
|----------|------------|
| GET | `/security-events` |
| GET | `/security-events/{id}` |
| POST | `/security-events/search` |
| GET | `/security-events/critical` |
| GET | `/security-events/open` |
| POST | `/security-events/{id}/acknowledge` |
| POST | `/security-events/{id}/resolve` |
| GET | `/security-events/export` |

## Example Event

```json
{
  "severity": "CRITICAL",
  "event": "MULTIPLE_FAILED_LOGIN",
  "user": "john",
  "ip": "103.x.x.x",
  "country": "RU",
  "device": "Chrome",
  "status": "OPEN"
}
```