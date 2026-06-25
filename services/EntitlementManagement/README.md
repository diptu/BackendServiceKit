# Entitlement Management Service

## Purpose

The Entitlement Management service manages business entitlements and feature capabilities assigned to users, organizations, or tenants.

An entitlement represents **what someone is allowed to have**, rather than low-level permissions or actions.

## Important

An entitlement is what someone is allowed to have.

Examples of entitlements:

```text id="k9d104"
✓ Can access Premium Reports
✓ Can use AI Assistant
✓ Can manage 500 users
```

Examples that are **not** entitlements:

```text id="q3t561"
✗ Can Edit Invoice
✗ Can Delete Report
✗ Can Create User
```

Those examples represent permissions and belong in authorization systems.

## Responsibilities

The Entitlement Management service handles:

* Grant entitlements
* Revoke entitlements
* Assign package capabilities
* Manage feature access
* Track entitlement assignments

## Entitlement Lifecycle

```text id="n4v820"
Create Entitlement
        ↓
Assign Entitlement
        ↓
Grant Access
        ↓
Use Feature
        ↓
Revoke Entitlement
```

## Ownership Model

An entitlement owns and manages the following attributes:

```text id="w8g291"
Entitlement
├── Name
├── Description
├── Target Entity
├── Limits
├── Status
└── Metadata
```

## Example Structure

Example entitlement object:

```json id="f7r632"
{
  "id": "premium_reports",
  "name": "Premium Reports",
  "description": "Access premium analytics dashboards",
  "limit": null,
  "status": "active"
}
```

Example with quota-based entitlement:

```json id="x2p460"
{
  "id": "managed_users",
  "name": "Managed Users",
  "limit": 500,
  "status": "active"
}
```

## API Endpoints

### Entitlement Management

```http id="j6w715"
POST   /entitlements
GET    /entitlements
GET    /entitlements/{id}
```

### Entitlement Assignment

```http id="u4m208"
POST   /entitlements/grants
POST   /entitlements/revoke
```

### Entitlement Queries

```http id="c8t304"
GET    /users/{id}/entitlements
GET    /tenants/{id}/entitlements
```

## Entitlement Relationships

```text id="b1k507"
Entitlement
├── Feature Access
├── Package Capabilities
├── Usage Limits
├── Users
└── Tenants
```
