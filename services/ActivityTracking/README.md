# Activity Tracking Service

## Responsibility

Tracks normal product usage.

Unlike Audit Logs, these are not security records.

## Examples

- Viewed Dashboard
- Opened Report
- Downloaded Invoice
- Created Project
- Edited Document
- Shared Workspace
- Uploaded Image
- Opened Settings
- Visited Billing Page

This service powers:

- Recent Activity
- User Timeline
- Product Analytics
- Feature Usage
- User Engagement
- DAU/MAU

## Example: Recent Activity

| Time | Activity |
|--------|------------|
| 10:30 | Opened Dashboard |
| 10:32 | Viewed Reports |
| 10:35 | Created Workspace |
| 10:36 | Uploaded PDF |

## APIs

| Method | Endpoint |
|----------|------------|
| POST | `/activities` |
| GET | `/activities` |
| GET | `/activities/me` |
| GET | `/activities/user/{id}` |
| GET | `/activities/tenant/{id}` |
| GET | `/activities/recent` |
| GET | `/activities/stats` |
| GET | `/activities/top-features` |

## Example Event

```json
{
  "user": "user123",
  "activity": "CREATED_WORKSPACE",
  "resource": "workspace456",
  "tenant": "tenant1",
  "timestamp": "...",
  "device": "Chrome",
  "location": "Dhaka"
}
```