# Subscription Management Service

## Purpose

The Subscription Management service manages tenant subscription plans and controls the lifecycle of tenant access to platform offerings.

The service tracks plan assignments, status, and subscription changes such as upgrades, downgrades, renewals, and cancellations.

## Example

Example tenant subscription:

```text id="sy4m72"
Tenant:
    Acme

Current Plan:
    Professional

Status:
    Active
```

## Responsibilities

The Subscription Management service handles:

* Create subscriptions
* Upgrade subscription plans
* Downgrade subscription plans
* Renew subscriptions
* Cancel subscriptions
* Track subscription status

## Subscription Lifecycle

```text id="v2k913"
Create Subscription
            ↓
Activate Plan
            ↓
Upgrade / Downgrade
            ↓
Renew Subscription
            ↓
Cancel Subscription
```

## Ownership Model

A subscription owns and manages the following attributes:

```text id="p6d528"
Subscription
├── Tenant
├── Plan
├── Status
├── Start Date
├── Renewal Date
└── Billing Metadata
```

## Example Structure

Example subscription object:

```json id="m8f315"
{
  "tenant_id": "tenant_acme",
  "plan": "Professional",
  "status": "active",
  "start_date": "2026-06-25",
  "renewal_date": "2027-06-25"
}
```

## API Endpoints

### Subscription Management

```http id="y5r107"
POST   /subscriptions
GET    /subscriptions
GET    /subscriptions/{id}
```

### Subscription Actions

```http id="w1n892"
POST   /subscriptions/{id}/upgrade
POST   /subscriptions/{id}/downgrade
POST   /subscriptions/{id}/renew
POST   /subscriptions/{id}/cancel
```

## Subscription Relationships

```text id="r9x463"
Subscription
├── Tenant
├── Plan
├── Status
├── Billing Information
├── Renewal Schedule
└── Lifecycle Events
```
