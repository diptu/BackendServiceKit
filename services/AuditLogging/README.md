# Audit Logging Service

## Responsibility

**Answer:**

Who performed what action, when, where, and was it successful?

Every important action inside the system creates an immutable audit record.

## Examples

- User logged in
- User created tenant
- Admin deleted user
- Permission granted
- Role removed
- API key created
- Subscription changed

Audit logs are primarily for accountability.

## Example Audit Record

**Time:** 10:31 AM  
**Actor:** Admin John  
**Action:** DELETE  
**User:** Alice  
**IP:** 203.10.20.1  
**Status:** SUCCESS  

## APIs

| Method | Endpoint |
|----------|------------|
| GET | `/audit-logs` |
| GET | `/audit-logs/{id}` |
| POST | `/audit-logs/search` |
| GET | `/audit-logs/export` |
| GET | `/audit-logs/user/{userId}` |
| GET | `/audit-logs/resource/{resourceId}` |
| GET | `/audit-logs/tenant/{tenantId}` |

## Typical Event

```json
{
  "actor": "admin123",
  "action": "DELETE_USER",
  "resource": "user456",
  "tenant": "tenant1",
  "time": "...",
  "ip": "...",
  "status": "SUCCESS"
}
```