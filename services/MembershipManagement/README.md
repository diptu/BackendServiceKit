# Membership Management Service

## Responsibility

A Membership represents the relationship between a user and a target entity within the platform.

This service centralizes membership management and answers a core question:

**Who belongs to what?**

Without a dedicated Membership service, every microservice would need to independently manage user-to-entity relationships.

## Examples

Membership relationships may include:

```text id="b4x201"
User
├── Organization
├── Workspace
├── Team
└── Group
```

Examples:

* User → Organization
* User → Workspace
* User → Team
* User → Group

## Membership Capabilities

The Membership service provides:

* Centralized relationship management
* Cross-service membership lookup
* Role assignment
* Membership status tracking
* Metadata association

## Ownership Model

A membership owns and manages the following attributes:

```text id="j5d702"
Membership
├── User
├── Target Entity
├── Role
├── Status
└── Metadata
```

## Example Structure

Example membership object:

```json id="n8f630"
{
  "user_id": "123",
  "entity_type": "workspace",
  "entity_id": "456",
  "role": "admin"
}
```

## API Endpoints

### Membership Management

```http id="v0r216"
POST   /memberships
GET    /memberships

GET    /memberships/{membership_id}
DELETE /memberships/{membership_id}

PATCH  /memberships/{membership_id}
```

### User Membership Queries

```http id="m3u901"
GET    /users/{user_id}/memberships
```

### Entity Membership Queries

```http id="f4w582"
GET    /organizations/{org_id}/memberships
GET    /workspaces/{workspace_id}/memberships
GET    /teams/{team_id}/memberships
GET    /groups/{group_id}/memberships
```

## Membership Relationships

```text id="z2t413"
Membership
├── User
├── Entity Type
│   ├── Organization
│   ├── Workspace
│   ├── Team
│   └── Group
├── Role
├── Status
└── Metadata
```
