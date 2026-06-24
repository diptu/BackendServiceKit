# User Management Service

## Purpose
Manages user accounts and identities.  
This is the authoritative source of user identity.

### Question it answers
* What users exist in the platform?

## Responsibilities
* User CRUD
* User status management
* Tenant membership
* User lifecycle
* User invitations
* Account activation
* Account suspension

## Owns
* `users`
* `tenant_memberships`
* `user_statuses`
* `invitations`

## API Endpoints

### Users
* `GET    /users`
* `POST   /users`
* `GET    /users/{user_id}`
* `PATCH  /users/{user_id}`
* `DELETE /users/{user_id}`

### Status
* `POST /users/{user_id}/activate`
* `POST /users/{user_id}/suspend`
* `POST /users/{user_id}/deactivate`

### Tenant Memberships
* `POST   /tenants/{tenant_id}/members`
* `DELETE /tenants/{tenant_id}/members/{user_id}`

### Invitations
* `POST /invitations`
* `GET  /invitations/{id}`