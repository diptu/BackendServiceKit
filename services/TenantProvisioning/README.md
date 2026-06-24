# Tenant Provisioning Service

## Purpose
Responsible for creating and configuring infrastructure and resources required for a new tenant.

## Responsibilities

- Create tenant database/schema
- Create storage buckets
- Create default roles
- Create default permissions
- Create default admin user
- Create default workspace
- Configure feature flags
- Set up DNS/domain
- Provision external integrations

## Owns

- **Provisioning workflows only**
- Does **not** own tenant business data

## Example Workflow

```text
Create Tenant Request
        |
        v
Create DB Schema
        |
        v
Create Storage
        |
        v
Create Default Roles
        |
        v
Create Admin User
        |
        v
Create Workspace
        |
        v
Provision Completed
```

## API Endpoints

| Method | Endpoint |
|----------|----------|
| POST | `/provisioning/tenants` |
| GET | `/provisioning/jobs` |
| GET | `/provisioning/jobs/{job_id}` |
| POST | `/provisioning/tenants/{tenant_id}/retry` |
| POST | `/provisioning/tenants/{tenant_id}/resources` |
| GET | `/provisioning/tenants/{tenant_id}/status` |

## Example Event

```json
{
  "event": "tenant.created",
  "tenant_id": "tenant_123"
}
```

**Behavior:**

The Provisioning Service subscribes to the `tenant.created` event and starts the tenant setup workflow automatically.