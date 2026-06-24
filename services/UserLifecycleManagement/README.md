# User Lifecycle Management Service

## Responsibility
Manages the entire lifecycle of a user account from creation to deletion.

## Scope
* Create users
* Update user information
* Activate/Deactivate users
* Suspend users
* Lock/Unlock users
* Terminate users
* Soft delete users
* Restore users
* User onboarding
* User offboarding

## Does NOT Handle
* Login
* Sessions
* MFA
* Password validation
* OAuth

## APIs

### Provisioning & Details
* `POST /users`
* `GET /users`
* `GET /users/{user_id}`
* `PATCH /users/{user_id}`
* `DELETE /users/{user_id}`

### Lifecycle & Account States
* `POST /users/{user_id}/activate`
* `POST /users/{user_id}/deactivate`
* `POST /users/{user_id}/suspend`
* `POST /users/{user_id}/unsuspend`
* `POST /users/{user_id}/lock`
* `POST /users/{user_id}/unlock`
* `POST /users/{user_id}/restore`

### Onboarding & Workflows
* `POST /users/{user_id}/onboard`
* `POST /users/{user_id}/offboard`
* `GET /users/{user_id}/status`