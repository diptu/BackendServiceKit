# Customer Portal Service

## Purpose

The Customer Portal Service provides a self-service UI/API layer that customers use to manage their account and subscription experience.

Examples of similar systems include:

* Stripe Customer Portal
* Azure Subscription Portal
* AWS Billing Console
* GitHub Billing Settings

This service primarily acts as an orchestration layer that aggregates and coordinates data from multiple backend services.

Typically, it consumes APIs from:

* Customer Account Service
* Billing Service
* Subscription Service
* Payment Service
* Tenant Service

---

## Responsibilities

The Customer Portal Service enables customers to:

* View account details
* Manage subscriptions
* Upgrade plans
* Download invoices
* Update payment methods
* View usage information
* Manage billing contacts
* Manage tenant settings
* Create support tickets

---

## Owns

The service generally owns very little business data.

Typical owned entities include:

* Portal preferences
* Portal settings
* Portal widgets
* Portal configuration

---

## Does NOT Own

The service does **not** own:

* Customers
* Subscriptions
* Billing records
* Payments
* Tenants
* Authentication and authorization

These entities belong to their respective domain services.

The Customer Portal Service consumes and orchestrates information from those services.

---

## API Endpoints

### Account

```http id="9fe2mv"
GET /portal/account
PUT /portal/account
```

### Subscription

```http id="2hs4kn"
GET  /portal/subscription
POST /portal/subscription/change-plan
POST /portal/subscription/cancel
```

### Billing

```http id="5yrm29"
GET /portal/invoices
GET /portal/invoices/{id}

GET /portal/payments
```

### Payment Methods

```http id="7lb3cw"
GET    /portal/payment-methods
POST   /portal/payment-methods
DELETE /portal/payment-methods/{id}
```

### Usage

```http id="3qhf9w"
GET /portal/usage
```

### Support

```http id="8gc6ea"
GET  /portal/tickets
POST /portal/tickets
```

---

## Architecture Relationship

```text id="f1mk8z"
                    Customer Portal
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼

 Customer Account    Subscription      Billing
     Service           Service         Service
         │                                │
         ▼                                ▼

      Tenant                        Tax Service
      Service                            │
                                          ▼
                                   Payment Service
```

---

## Example Flow

```text id="k84nm2"
Customer
    ↓
Customer Portal
    ↓
GET /portal/subscription
    ↓
Subscription Service
    ↓
Returns subscription details
```

---

## Service Interaction Notes

* Acts primarily as an orchestration layer rather than a core business domain service.
* Aggregates information from multiple backend systems into a unified customer experience.
* May implement API composition patterns to reduce frontend complexity.
* Typically serves both web and mobile applications.
* Should avoid duplicating business logic from underlying services.
* Uses customer identifiers and tenant context when interacting with downstream services.

---

## Future Enhancements

Potential future capabilities:

* Dashboard customization
* Real-time notifications
* AI-powered account recommendations
* Self-service feature management
* Integrated customer support chat
* Personalized widgets
* Cross-service analytics dashboards
