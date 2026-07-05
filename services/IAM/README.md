# Identity & Access Management (IAM) Service

The IAM Service is the central system responsible for identities, roles, permissions, policies, groups, attributes, and access governance.

Think of it as the "source of truth" for all identities in the platform.

Responsibilities
User lifecycle management
Role management
Permission management
Group management
Tenant membership management
Attribute management
Access governance
Identity federation metadata
Policy storage
Entitlement management
Access reviews
Owns
Users
Groups
Roles
Permissions
Attributes
Entitlements
Memberships


## IAM API Endpoints
### Users

```bash

GET    /users
POST   /users

GET    /users/{user_id}
PATCH  /users/{user_id}
DELETE /users/{user_id}
```
### Roles

```bash
GET    /roles
POST   /roles

GET    /roles/{role_id}
PATCH  /roles/{role_id}
DELETE /roles/{role_id}
```

### Permissions

```bash
GET    /permissions
POST   /permissions

GET    /permissions/{permission_id}
PATCH  /permissions/{permission_id}
DELETE /permissions/{permission_id}
```

### Groups

```bash
GET    /groups
POST   /groups

POST   /groups/{group_id}/members
DELETE /groups/{group_id}/members/{user_id}

```

### User Roles

```bash
GET    /user-roles/{user_id}
POST   /user-roles/{user_id}
DELETE /user-roles/{user_id}/{role_id}

```
Mounted at `/user-roles/{user_id}`, not the literal `/users/{user_id}/roles`
implied above — APIGateway's `/api/v1/users` prefix now points at
UserManagement (see `services/UserManagement/TODO.md`), and its route
registry does plain string-prefix matching with no path templating, so a
nested `/users/{user_id}/roles` path would be silently swallowed by that
prefix.

### Attributes
```bash
GET    /user-attributes/{user_id}
POST   /user-attributes/{user_id}
PATCH  /user-attributes/{user_id}/{attribute_id}
DELETE /user-attributes/{user_id}/{attribute_id}
```
Mounted at `/user-attributes/{user_id}`, not the literal `/users/{user_id}/attributes`
implied above — APIGateway's `/api/v1/users` prefix now points at
UserManagement (see `services/UserManagement/TODO.md`), and its route
registry does plain string-prefix matching with no path templating, so a
nested `/users/{user_id}/attributes` path would also be swallowed by that
prefix.

### Tenant Memberships
```bash
POST   /tenants/{tenant_id}/members
DELETE /tenants/{tenant_id}/members/{user_id}
Entitlements
GET    /entitlements
POST   /entitlements
```

### Audit Events
```bash
GET /audit-events
```
Read-only. Records every role assignment, role<->permission linkage
change, group membership change, tenant membership change, and
entitlement grant/revoke — see `app/models/audit_event.py`. Supports
`subject_user_id`/`resource_type` filters and cursor pagination.
`actor_id` (from a caller-supplied `performed_by` field, where the
corresponding write endpoint accepts one) is unverified — no
Authentication Service exists yet in this repo to cryptographically
confirm who is calling.

## Architecture
```text

                    ┌────────────────────┐
                    │    User Service     │
                    │  (Source of Truth)  │
                    └─────────┬──────────┘
                              │
                     UserCreated
                     UserUpdated
                     UserDeleted
                              │
                      RabbitMQ / Kafka
                              │
                              ▼
                    ┌────────────────────┐
                    │     IAM Service     │
                    │   User Projection   │
                    └────────────────────┘
   ```