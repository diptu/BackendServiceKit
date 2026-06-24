# ReBAC Management Service

## Purpose
Manages relationships between entities.

ReBAC focuses on:
`User → Relationship → Resource` (instead of roles).

### Question it answers
* What relationship does this user have with this resource?

## Responsibilities
* Relationship management
* Resource ownership
* Resource sharing
* Graph relationship management
* Delegation

## Owns
* `relationships`
* `resource_owners`
* `resource_shares`

## Example
* `user123 OWNER invoice789`
* `user456 VIEWER invoice789`
* `user999 EDITOR invoice789`

## API Endpoints

### Relationships
* `GET    /relationships`
* `POST   /relationships`
* `DELETE /relationships/{relationship_id}`

### Resource Ownership
* `POST /resources/{resource_id}/owner`
* `GET  /resources/{resource_id}/owner`

### Sharing
* `POST /resources/{resource_id}/share`
* `DELETE /resources/{resource_id}/share/{user_id}`

### Graph Queries
* `POST /relationships/check`
* `POST /relationships/expand`
