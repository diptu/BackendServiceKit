# Payment Service

## Responsibility

The Payment Service collects money from customers and manages payment processing workflows.

This service integrates with external payment providers and handles payment execution, transaction tracking, refunds, and payment events.

Supported integrations:

* Stripe
* PayPal
* Razorpay
* bKash

The service handles:

* Card payments
* Wallet payments
* Refunds
* Failed payments
* Payment webhooks

The service does **not**:

* Calculate billing amounts
* Generate invoices
* Track resource usage
* Enforce quotas

---

## Dependencies

Consumes:

* Billing Service
* Invoice Service

Integrates with:

* Stripe
* PayPal
* Razorpay
* bKash

Provides:

* Payment execution
* Transaction processing
* Refund handling
* Payment status updates

---

## Example

### Invoice

```text
$88
```

Payment Service charges the selected payment method.

### Result

```text
Payment Success
```

Invoice status becomes:

```text
Paid
```

---

## Core Concepts

### Payment

Represents a payment attempt or completed payment.

Attributes:

| Field      | Type     | Description        |
| ---------- | -------- | ------------------ |
| id         | UUID     | Payment identifier |
| invoice_id | String   | Related invoice    |
| amount     | Decimal  | Payment amount     |
| status     | String   | Payment status     |
| created_at | DateTime | Payment timestamp  |

---

### PaymentMethod

Represents a customer payment source.

Examples:

* Credit card
* Debit card
* Wallet
* Bank account

Attributes:

| Field     | Type   | Description               |
| --------- | ------ | ------------------------- |
| id        | UUID   | Payment method identifier |
| tenant_id | String | Tenant identifier         |
| type      | String | Payment type              |
| provider  | String | Payment provider          |

---

### Transaction

Represents an external provider transaction.

Attributes:

| Field                   | Type    | Description            |
| ----------------------- | ------- | ---------------------- |
| id                      | UUID    | Transaction identifier |
| payment_id              | UUID    | Related payment        |
| provider_transaction_id | String  | External provider ID   |
| amount                  | Decimal | Transaction amount     |
| status                  | String  | Transaction status     |

---

### Refund

Represents returned payment amounts.

Attributes:

| Field      | Type    | Description        |
| ---------- | ------- | ------------------ |
| id         | UUID    | Refund identifier  |
| payment_id | UUID    | Associated payment |
| amount     | Decimal | Refund amount      |
| reason     | String  | Refund reason      |
| status     | String  | Refund status      |

---

## Database Entities

* Payment
* PaymentMethod
* Transaction
* Refund

---

## API Endpoints

### Payments

| Method | Endpoint         | Description              |
| ------ | ---------------- | ------------------------ |
| POST   | `/payments`      | Create payment           |
| GET    | `/payments`      | Retrieve payments        |
| GET    | `/payments/{id}` | Retrieve payment details |

---

### Refund Operations

| Method | Endpoint           | Description  |
| ------ | ------------------ | ------------ |
| POST   | `/payments/refund` | Issue refund |

---

### Webhooks

| Method | Endpoint            | Description               |
| ------ | ------------------- | ------------------------- |
| POST   | `/payments/webhook` | Process provider webhooks |

---

### Payment Methods

| Method | Endpoint                | Description              |
| ------ | ----------------------- | ------------------------ |
| GET    | `/payment-methods`      | Retrieve payment methods |
| POST   | `/payment-methods`      | Add payment method       |
| DELETE | `/payment-methods/{id}` | Remove payment method    |

---

## Example Request

### POST /payments

```json
{
  "invoice_id": "inv_123",
  "payment_method": "card"
}
```

### Response

```json
{
  "status": "success",
  "transaction_id": "txn_456"
}
```

---

## Typical Flow

1. Invoice is generated.
2. Customer selects payment method.
3. Payment Service sends request to provider.
4. Provider processes payment.
5. Transaction result is returned.
6. Invoice status is updated.
7. Subscription or account state is updated.

---

## End-to-End System Flow

```text
User uploads document
        ↓
Usage Metering
records +1 document
        ↓
Quota Service
checks limit
        ↓
Billing Service
calculates charges
        ↓
Invoice Service
creates invoice
        ↓
Payment Service
collects money
        ↓
Subscription updated
```

---

## Notes

* Payment operations should be idempotent.
* Sensitive payment data should never be stored directly.
* Webhook events should be verified before processing.
* Retry mechanisms should exist for temporary failures.
* Payment state transitions should be tracked for auditing.
* Refunds should maintain complete transaction history.
