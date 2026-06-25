# Plan Management Service

## Purpose

The Plan Management service defines subscription plans offered by the platform.

This service is responsible for maintaining plan definitions, pricing models, limits, and included features.

The service does **not** manage customers or subscriptions.

Its responsibility is limited to plan configuration and lifecycle management.

## Examples

Common plan definitions may include:

```text id="tp4m61"
Starter
Professional
Enterprise
```

## Responsibilities

The Plan Management service handles:

* Create plans
* Define pricing
* Define usage limits
* Define included features
* Manage plan lifecycle
* Activate or archive plans

## Plan Lifecycle

```text id="q9f734"
Create Plan
        ↓
Define Pricing
        ↓
Configure Limits
        ↓
Add Features
        ↓
Activate Plan
        ↓
Archive Plan
```

## Ownership Model

A plan owns and manages the following attributes:

```text id="u7k320"
Plan
├── Name
├── Pricing
├── Limits
├── Features
├── Status
└── Metadata
```

## Example Structure

Example plan object:

```json id="j4r906"
{
  "id": "plan_professional",
  "name": "Professional",
  "price": 49.99,
  "billing_cycle": "monthly",
  "limits": {
    "users": 100,
    "storage_gb": 500
  },
  "features": [
    "advanced_reporting",
    "priority_support"
  ],
  "status": "active"
}
```

## API Endpoints

### Plan Management

```http id="m3v125"
POST   /plans
GET    /plans
GET    /plans/{id}
PATCH  /plans/{id}
DELETE /plans/{id}
```

### Plan Lifecycle Actions

```http id="d8x417"
POST   /plans/{id}/activate
POST   /plans/{id}/archive
```

## Plan Relationships

```text id="r2z680"
Plan
├── Pricing
├── Limits
├── Features
├── Status
└── Subscription Consumers
    └── Tenant Subscriptions
```
