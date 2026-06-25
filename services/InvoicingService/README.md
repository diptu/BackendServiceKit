# Invoicing Service

## Responsibility

The Invoicing Service creates official invoices and accounting documents based on billing calculations.

The Billing Service determines the amount owed, while the Invoicing Service generates legally and financially usable invoice records.

It answers questions such as:

* What invoice was generated for a tenant?
* What is the invoice status?
* Has an invoice been sent?
* Can an invoice be downloaded?

The service does **not**:

* Calculate pricing
* Determine subscription costs
* Process payments
* Enforce quotas

---

## Dependencies

Consumes:

* Billing Service

Provides:

* Invoice generation
* PDF generation
* Invoice delivery
* Invoice storage
* Invoice status tracking

---

## Example

### Billing Result

```text
Tenant owes: $88
```

### Generated Invoice

```text
Invoice #: INV-2026-0001
Amount: $88
Due Date: 2026-08-01
```

Additional actions:

* PDF generated
* Invoice emailed
* Invoice stored

---

## Core Concepts

### Invoice

Represents an official billing document issued to a customer.

Attributes:

| Field      | Type     | Description                   |
| ---------- | -------- | ----------------------------- |
| id         | UUID     | Invoice identifier            |
| invoice_no | String   | Human-readable invoice number |
| tenant_id  | String   | Tenant identifier             |
| amount     | Decimal  | Invoice total                 |
| due_date   | Date     | Payment due date              |
| status     | String   | Invoice state                 |
| created_at | DateTime | Creation timestamp            |

---

### InvoiceItem

Represents individual line items included in an invoice.

Examples:

* Subscription fee
* Storage overage
* Additional users
* Taxes

Attributes:

| Field       | Type    | Description      |
| ----------- | ------- | ---------------- |
| id          | UUID    | Item identifier  |
| invoice_id  | UUID    | Related invoice  |
| description | String  | Item description |
| quantity    | Number  | Quantity         |
| amount      | Decimal | Item amount      |

---

### InvoiceTemplate

Represents configurable invoice layouts and branding.

Examples:

* Default template
* Enterprise template
* Region-specific template

Attributes:

| Field  | Type   | Description            |
| ------ | ------ | ---------------------- |
| id     | UUID   | Template identifier    |
| name   | String | Template name          |
| layout | JSON   | Template configuration |

---

### InvoiceStatus

Represents invoice lifecycle states.

Examples:

* Draft
* Issued
* Sent
* Paid
* Overdue
* Cancelled

Attributes:

| Field | Type   | Description       |
| ----- | ------ | ----------------- |
| id    | UUID   | Status identifier |
| name  | String | Status value      |

---

## Database Entities

* Invoice
* InvoiceItem
* InvoiceTemplate
* InvoiceStatus

---

## API Endpoints

### Invoice Management

| Method | Endpoint         | Description              |
| ------ | ---------------- | ------------------------ |
| POST   | `/invoices`      | Create invoice           |
| GET    | `/invoices`      | Retrieve invoices        |
| GET    | `/invoices/{id}` | Retrieve invoice details |

---

### Invoice Operations

| Method | Endpoint                | Description    |
| ------ | ----------------------- | -------------- |
| POST   | `/invoices/{id}/send`   | Send invoice   |
| POST   | `/invoices/{id}/cancel` | Cancel invoice |

---

### Document Operations

| Method | Endpoint                  | Description               |
| ------ | ------------------------- | ------------------------- |
| GET    | `/invoices/{id}/pdf`      | Generate invoice PDF      |
| GET    | `/invoices/{id}/download` | Download invoice document |

---

## Example Response

```json
{
  "invoice_no": "INV-2026-0001",
  "amount": 88,
  "status": "issued"
}
```

---

## Typical Flow

1. Billing Service calculates charges.
2. Billing result is sent to the Invoicing Service.
3. Invoice record is created.
4. Invoice items are generated.
5. PDF document is produced.
6. Invoice is stored.
7. Invoice is sent to the customer.
8. Invoice status is updated throughout its lifecycle.

---

## Notes

* Invoice numbers should be unique and sequential.
* Generated invoices should remain immutable after issuance.
* PDF generation should support branding and localization.
* Historical invoices must be preserved for auditing purposes.
* Invoice templates should support customization.
* Status transitions should be tracked for compliance and reporting.
