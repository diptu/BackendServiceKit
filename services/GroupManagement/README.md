# Group Management Service

## Responsibility

A Group is an authorization-based collection of members used for managing access and permissions across the platform.

Groups are primarily intended for access control rather than operational collaboration.

## Examples

Common groups within an organization may include:

```text id="t9m231"
Finance Approvers
HR Managers
Support Agents
SOC Analysts
```

## Group Usage

Groups are commonly used by:

* RBAC (Role-Based Access Control)
* ABAC (Attribute-Based Access Control)
* ReBAC (Relationship-Based Access Control)

## Ownership Model

A group owns and manages the following entities:

```text id="n4b763"
Group
├── Members
├── Permissions
├── Policies
└── Roles
```

## Example Structure

Example group configuration:

```text id="u6x913"
Group: Finance Approvers

Members:
- Alice
- Bob
- Charlie

Permissions:
- approve_invoice
```

## API Endpoints

### Group Management

```http id="d81qp4"
POST   /groups
GET    /groups
GET    /groups/{group_id}
PATCH  /groups/{group_id}
DELETE /groups/{group_id}
```

### Group Membership

```http id="m2k847"
POST   /groups/{group_id}/members
DELETE /groups/{group_id}/members/{member_id}

GET    /groups/{group_id}/members
```

### Group Roles

```http id="y53l21"
POST   /groups/{group_id}/roles
DELETE /groups/{group_id}/roles/{role_id}
```

### Group Permissions

```http id="w81z09"
POST   /groups/{group_id}/permissions
DELETE /groups/{group_id}/permissions/{permission_id}
```

## Group Relationships

```text id="r0f682"
Organization
└── Workspace
    └── Group
        ├── Members
        ├── Roles
        ├── Permissions
        └── Policies
```
