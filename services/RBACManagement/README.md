# RBAC Management Service

## Purpose
Manages roles and permissions.

RBAC focuses on:
`User → Role → Permission`

### Question it answers
* Which permissions belong to which role?

## Responsibilities
* Role management
* Permission management
* Role assignment
* Permission assignment
* Role hierarchy

## Owns
* `roles`
* `permissions`
* `role_permissions`
* `user_roles`

## Example
* **Admin**
  ├── `user:create`
  ├── `user:update`
  └── `user:delete`

## API Endpoints

### Roles
* `GET    /roles`
* `POST   /roles`
* `GET    /roles/{role_id}`
* `PATCH  /roles/{role_id}`
* `DELETE /roles/{role_id}`

### Permissions
* `GET    /permissions`
* `POST   /permissions`
* `GET    /permissions/{permission_id}`
* `PATCH  /permissions/{permission_id}`
* `DELETE /permissions/{permission_id}`

### Role Assignments
* `POST   /users/{user_id}/roles`
* `DELETE /users/{user_id}/roles/{role_id}`

### Permission Assignments
* `POST   /roles/{role_id}/permissions`
* `DELETE /roles/{role_id}/permissions/{permission_id}`