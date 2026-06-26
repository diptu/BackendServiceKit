# Change History Service

## Responsibility

Stores how a resource changed over time.

This is object versioning.

## Examples

### Role Change

**Before:** Viewer  
**After:** Admin  

### Policy Change

**Old:** Allow Sales  
**New:** Allow Finance  

### User Change

**Old Email:** abc@gmail.com  
**New Email:** xyz@gmail.com  

Very similar to Git history.

## APIs

| Method | Endpoint |
|----------|------------|
| GET | `/history` |
| GET | `/history/{resourceType}/{resourceId}` |
| GET | `/history/{id}` |
| POST | `/history/compare` |
| GET | `/history/versions` |
| POST | `/history/{id}/restore` |
| GET | `/history/export` |

## Example Version Flow

```text
Version 1
   ↓
Version 2
   ↓
Version 3
   ↓
Version 4
```

## Example Record

```json
{
  "resourceType": "USER",
  "resourceId": "user123",
  "version": 4,
  "changedBy": "admin456",
  "timestamp": "...",
  "changes": {
    "email": {
      "old": "abc@gmail.com",
      "new": "xyz@gmail.com"
    }
  }
}
```