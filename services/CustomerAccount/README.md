# Customer Account Service

## Purpose

The Customer Account Service acts as the CRM-like master record for customer organizations or customer accounts.

In a SaaS platform, a customer typically represents a company or organization rather than individual users.

Examples:

* OpenAI
* Google
* Microsoft
* ABC Corporation

Users within those organizations are managed separately and belong to Identity and Access Management (IAM).

---

## Responsibilities

The Customer Account Service handles:

* Customer lifecycle management
* Customer profile storage
* Customer contacts
* Customer segmentation
* Customer status management
* Customer ownership
* Customer success data
* Customer metadata management

---

## Owns

The service owns and manages:

* Customer
* Customer contacts
* Customer addresses
* Customer metadata
* Customer status

---

## Does NOT Own

The service does **not** own:

* Authentication
* Users
* Roles
* Permissions

These responsibilities belong to the IAM service.

---

## API Endpoints

### Customer Management

```http
GET    /customers
POST   /customers

GET    /customers/{id}
PUT    /customers/{id}

DELETE /customers/{id}
```

### Customer Contacts

```http
GET    /customers/{id}/contacts
POST   /customers/{id}/contacts
```

### Customer Related Data

```http
GET    /customers/{id}/subscriptions
GET    /customers/{id}/invoices
GET    /customers/{id}/usage
```

---

## Example Customer Record

```json
{
  "id": "cust_001",
  "name": "ABC Corporation",
  "industry": "Finance",
  "employee_count": 500,
  "status": "active"
}
```

---

## Example Flow

```text
Sales Team
      ↓
POST /customers
      ↓
Customer Account Service
      ↓
Stores customer profile and metadata
```

---

## Service Interaction Notes

* Serves as the central source of truth for customer organizations.
* Stores business-related customer information independently from authentication systems.
* Can be queried by Billing, Subscription, Usage, CRM, and Reporting services.
* Links to external services through customer identifiers.
* Customer contacts represent business contacts rather than application users.
* Subscription, invoice, and usage information are retrieved from external services.

---

## Future Enhancements

Potential future capabilities:

* Customer hierarchy support (parent/subsidiary relationships)
* Multi-tenant organization structures
* CRM integrations
* Customer health scoring
* Customer success workflows
* Tagging and advanced segmentation
* Customer analytics and insights
