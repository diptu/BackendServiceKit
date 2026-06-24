# Authorization Service

Authorization determines whether an authenticated identity can perform an action.

This service becomes the **Policy Decision Point (PDP)**.

For ABAC (Attribute-Based Access Control) systems, this service is often implemented using:
* OpenFGA
* Open Policy Agent (OPA)
* Cedar
* AWS Verified Permissions
* Custom Policy Engine

## Responsibilities
* Policy evaluation
* Access decisions
* ABAC evaluation
* RBAC evaluation
* ReBAC evaluation
* Policy simulation
* Permission checks

## Owns
* `policies`
* `policy_versions`
* `authorization_decisions`
* `policy_audit_logs`

## Authorization API Endpoints

### Main Decision Endpoint
* `POST /authorize`

**Request:**
```json
{
  "subject": "user_123",
  "action": "invoice.read",
  "resource": "invoice_456"
}
```

**Response:**
```json
{
  "allowed": true
}
```

### Batch Authorization
* `POST /authorize/batch`

### Policy Evaluation
* `POST /policies/evaluate`

### Policy Simulation
* `POST /policies/simulate`

### Policy Management
* `GET    /policies`
* `POST   /policies`
* `GET    /policies/{policy_id}`
* `PATCH  /policies/{policy_id}`
* `DELETE /policies/{policy_id}`

### Decision Audit
* `GET /authorization/decisions`

## Typical Flow

```
1. User logs in
          │
          ▼
Authentication Service
          │
          ▼
Issues JWT

2. User calls API
          │
          ▼
API Gateway

3. Gateway validates JWT
          │
          ▼
Authentication Service

4. Gateway requests decision
          │
          ▼
Authorization Service
(POST /authorize)

5. Authorization Service retrieves Roles, Permissions, Attributes, Tenant Memberships
          │
          ▼
IAM Service

6. Authorization returns {"allowed": true}

7. API executes request
```

## Separation of Concerns

### IAM Service
Stores identities, roles, permissions, attributes.

### Authentication Service
Verifies identity and issues tokens.

### Authorization Service
Evaluates policies and makes access decisions.

## Common Enterprise Architecture

```
IAM Service
    │
    ▼
Authentication Service
    │
    ▼
Authorization Service
    │
    ▼
Business Services
```