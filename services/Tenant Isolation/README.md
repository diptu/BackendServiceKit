# Tenant Isolation Service

## Purpose

Ensures that Tenant A can never access Tenant B's resources.

This is one of the most critical security services in a multi-tenant SaaS architecture.

## Responsibilities

- Resolve current tenant context
- Validate tenant boundaries
- Enforce tenant filters
- Prevent cross-tenant access
- Perform tenant-aware authorization checks
- Validate tenant-scoped queries
- Propagate tenant context across services

## Owns

- **Tenant context**
- **Isolation policies**
- **Cross-tenant validation logic**

## Example Workflow

### User Context

```json
{
  "user_id": "u123",
  "tenant_id": "tenant_a"
}
```

### Incoming Request

```http
GET /documents/doc_001
```

### Isolation Validation

```text
Does doc_001 belong to tenant_a?
        |
        +---- Yes --> Allow Request
        |
        +---- No  --> 403 Forbidden
```

## API Endpoints

> These endpoints are typically internal-only and consumed by other services.

| Method | Endpoint |
|----------|----------|
| POST | `/isolation/validate` |
| POST | `/isolation/check-access` |
| POST | `/isolation/resolve-context` |
| POST | `/isolation/validate-resource` |
| POST | `/isolation/validate-query` |
| GET | `/isolation/policies` |
| PATCH | `/isolation/policies/{policy_id}` |

## Example Request

```json
{
  "tenant_id": "tenant_a",
  "resource_id": "doc_123",
  "resource_type": "document"
}
```

## Example Response

```json
{
  "allowed": true
}
```

## Behavior

The Tenant Isolation Service validates that every request, resource, and query remains within the boundaries of the requesting tenant. Any cross-tenant access attempt is denied before reaching the target resource.