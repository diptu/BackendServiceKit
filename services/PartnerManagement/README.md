# Partner Management Service

## Purpose

The Partner Management Service manages business partners that resell, distribute, or manage access to the SaaS platform.

Partners may onboard and manage their own customers while earning commissions or participating in revenue-sharing agreements.

Example structure:

```text
OpenAI SaaS
 ├── Partner A
 │    ├── Customer 1
 │    ├── Customer 2
 │
 └── Partner B
      ├── Customer 3
      └── Customer 4
```

Partners act as an intermediary layer between the SaaS provider and customer organizations.

---

## Responsibilities

The Partner Management Service handles:

* Partner lifecycle management
* Reseller agreement management
* Commission management
* Revenue-sharing configuration
* Partner tier management
* Partner-managed customer relationships
* Managed tenant assignment
* Partner analytics and reporting

---

## Owns

The service owns and manages:

* Partners
* Reseller agreements
* Commission rates
* Revenue sharing rules
* Partner tiers
* Managed tenants

---

## Does NOT Own

The service does **not** own:

* Customers
* Authentication
* Users
* Billing transactions
* Payments
* Subscriptions

These responsibilities belong to their respective services.

The Partner Management Service references and coordinates those entities where required.

---

## API Endpoints

### Partner Management

```http id="2h7lbm"
POST   /partners
GET    /partners
GET    /partners/{partner_id}
PATCH  /partners/{partner_id}
DELETE /partners/{partner_id}
```

### Partner Users

```http id="5kd8na"
POST /partners/{partner_id}/users
GET  /partners/{partner_id}/users
```

### Partner Tenants

```http id="7shq4c"
POST /partners/{partner_id}/tenants
GET  /partners/{partner_id}/tenants
```

### Commission Management

```http id="8ge6pm"
POST /partners/{partner_id}/commission-rules
GET  /partners/{partner_id}/commissions
```

### Partner Analytics

```http id="4ra2fv"
GET /partners/{partner_id}/dashboard
```

---

## Example Flow

```text id="p91fce"
New Partner Registration
          ↓
POST /partners
          ↓
Partner Management Service
          ↓
Create partner profile
          ↓
Configure commission rules
          ↓
Assign partner tier
```

---

## Example Partner Record

```json id="3zb9wl"
{
  "id": "partner_001",
  "name": "Global SaaS Resellers Ltd",
  "tier": "Gold",
  "commission_rate": 15,
  "managed_tenants": 45,
  "status": "active"
}
```

---

## Architecture Relationship

```text id="n6d2ks"
                   Partner Management
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼

     Customer         Subscription       Billing
      Service            Service          Service
          │                                    │
          ▼                                    ▼

      Tenant                           Payment
      Service                           Service
```

---

## Service Interaction Notes

* Enables indirect sales and reseller ecosystems.
* Partners may manage multiple customer accounts and tenants.
* Revenue-sharing and commission rules may vary based on partner tier.
* Partner users may have delegated administrative permissions.
* Works closely with Customer, Billing, and Subscription services.
* Analytics dashboards may aggregate data from multiple systems.

---

## Future Enhancements

Potential future capabilities:

* Multi-level partner hierarchy support
* Affiliate program integration
* Automated commission payouts
* Partner certification programs
* Performance-based tier upgrades
* Lead distribution workflows
* Partner marketplace capabilities
