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
POST   /users/{user_id}/roles
DELETE /users/{user_id}/roles/{role_id}

```

### Attributes
```bash
GET    /users/{user_id}/attributes
POST   /users/{user_id}/attributes
PATCH  /users/{user_id}/attributes/{attribute_id}
DELETE /users/{user_id}/attributes/{attribute_id}
```

### Tenant Memberships
```bash
POST   /tenants/{tenant_id}/members
DELETE /tenants/{tenant_id}/members/{user_id}
Entitlements
GET    /entitlements
POST   /entitlements
```