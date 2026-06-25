# Role Management Service

## Responsibility

A Role represents a business-level responsibility or position assigned to users within the platform.

Roles define what a user is within the organization structure, but do not directly define access permissions.

Examples include organizational responsibilities such as administrators, managers, and employees.

## Examples

Common business roles may include:

```text id="q8f620"
Admin
Manager
Employee
Auditor
Tenant Owner
```

## Role Capabilities

The Role service provides:

* Centralized role definitions
* Role lifecycle management
* Role assignment to users
* User role lookup

## Important Notes

The Role service **does not manage permissions**.

Its responsibility is limited to maintaining business roles and assignments.

Permission evaluation and authorization logic should be handled by separate services.

## Ownership Model

A role owns and manages the following attributes:

```text id="w5m291"
Role
├── ID
├── Name
├── Description
└── Assigned Users
```

## Example Structure

Example role object:

```json id="p9d438"
{
  "id": "role_admin",
  "name": "Admin",
  "description": "Tenant administrator"
}
```

## API Endpoints

### Role Management

```http id="t2j104"
POST   /roles
GET    /roles
GET    /roles/{role_id}
PATCH  /roles/{role_id}
DELETE /roles/{role_id}
```

### Role Assignment

```http id="z6u917"
POST   /roles/{role_id}/users
DELETE /roles/{role_id}/users/{user_id}

GET    /users/{user_id}/roles
```

## API Example

Create a new role:

```http id="c4n753"
POST /roles
```

Request body:

```json id="m1r684"
{
  "name": "Manager"
}
```

## Role Relationships

```text id="f7s520"
Role
├── Name
├── Description
└── Users
    ├── User A
    ├── User B
    └── User C
```
