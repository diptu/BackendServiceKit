# Permission Management Service

## Responsibility

A Permission represents an action that may be performed on a specific resource within the platform.

Permissions define *what actions are possible*, but they do not determine *who can perform them*.

Permissions are intended to be reusable and composable across roles and authorization models.

## Examples

Common permissions may include:

```text id="q4x816"
user:create
user:update
user:delete

document:read
document:update

invoice:approve
```

## Permission Capabilities

The Permission service provides:

* Centralized permission definitions
* Permission lifecycle management
* Resource-action mapping
* Permission assignment to roles

## Important Notes

The Permission service **does not know users**.

The Permission service **does not know ownership**.

The Permission service only defines actions.

Authorization decisions should be evaluated by higher-level authorization services.

## Ownership Model

A permission owns and manages the following attributes:

```text id="j8r504"
Permission
├── ID
├── Resource
└── Action
```

## Example Structure

Example permission object:

```json id="z3p761"
{
  "id": "document.read",
  "resource": "document",
  "action": "read"
}
```

## API Endpoints

### Permission Management

```http id="m7d123"
POST   /permissions
GET    /permissions
GET    /permissions/{permission_id}
PATCH  /permissions/{permission_id}
DELETE /permissions/{permission_id}
```

### Role-Permission Mapping

```http id="n5y408"
POST   /roles/{role_id}/permissions
DELETE /roles/{role_id}/permissions/{permission_id}

GET    /roles/{role_id}/permissions
```

## API Example

Create a permission:

```json id="x6w914"
{
  "resource": "document",
  "action": "read"
}
```

## Permission Relationships

```text id="h1u693"
Permission
├── Resource
│   ├── User
│   ├── Document
│   ├── Invoice
│   └── Project
└── Action
    ├── Create
    ├── Read
    ├── Update
    └── Delete
```
