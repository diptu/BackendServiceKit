# Team Management Service

## Responsibility

A Team is an operational working unit within a workspace. Teams organize people around a specific function, domain, or responsibility area and provide ownership boundaries for work and resources.

## Example

An Engineering Workspace may be organized into multiple teams:

```text id="rf3d81"
Engineering Workspace
├── Backend Team
├── Frontend Team
├── DevOps Team
└── QA Team
```

## Team Capabilities

Teams exist to:

* Assign work
* Assign permissions
* Manage ownership
* Route notifications

## Ownership Model

A team owns and manages the following entities:

```text id="m8t412"
Team
├── Members
├── Roles
├── Projects
└── Resources
```

## API Endpoints

### Team Management

```http id="h40dt3"
POST   /teams
GET    /teams
GET    /teams/{team_id}
PATCH  /teams/{team_id}
DELETE /teams/{team_id}
```

### Team Membership

```http id="k6zq95"
POST   /teams/{team_id}/members
DELETE /teams/{team_id}/members/{member_id}

GET    /teams/{team_id}/members
GET    /teams/{team_id}/roles
```

### Team Lifecycle

```http id="t9wv17"
POST   /teams/{team_id}/archive
POST   /teams/{team_id}/restore
```

## Team Relationships

```text id="g4nr20"
Workspace
└── Team
    ├── Members
    ├── Roles
    ├── Projects
    └── Resources
```
