# Attribute-Based Access Control (ABAC) Services

## 1. ABAC Policy Management Service

### Purpose
* Stores and manages authorization policies.
* Responsible for creating, updating, versioning, approving, and publishing policies.
* **Does not** make access decisions.

### Question it answers
> "What policies exist?"

### Responsibilities
* Create policies
* Update policies
* Delete policies
* Policy versioning
* Policy approval workflow
* Policy publishing
* Policy rollback
* Policy lifecycle management

### Owns
* `policies`
* `policy_versions`
* `policy_drafts`
* `policy_approvals`

### Example Policy
```json
{
  "effect": "allow",
  "subject.department": "finance",
  "resource.type": "invoice",
  "action": "read"
}
```

### API Endpoints

#### Policies
* `GET /policies`
* `POST /policies`
* `GET /policies/{policy_id}`
* `PATCH /policies/{policy_id}`
* `DELETE /policies/{policy_id}`

#### Policy Versions
* `GET /policies/{policy_id}/versions`
* `POST /policies/{policy_id}/publish`
* `POST /policies/{policy_id}/rollback`

#### Approval Workflow
* `POST /policies/{policy_id}/submit`
* `POST /policies/{policy_id}/approve`
* `POST /policies/{policy_id}/reject`

---

## 2. ABAC Policy Evaluation Engine Service

### Purpose
* Evaluates policies and returns authorization decisions.
* Acts as the **Policy Decision Point (PDP)**.
* **Never** stores users, roles, or permissions.

### Question it answers
> "Can this subject perform this action on this resource?"

### Responsibilities
* Evaluate policies
* Make authorization decisions
* ABAC enforcement
* Attribute resolution
* Policy simulation
* Decision caching
* Decision audit logging

### Owns
* `authorization_decisions`
* `decision_cache`
* `evaluation_logs`

### API Endpoints

#### Authorization
* `POST /authorize`

##### Request Body Example
```json
{
  "subject": "user_123",
  "action": "invoice.read",
  "resource": "invoice_789"
}
```

#### Batch Authorization
* `POST /authorize/batch`

#### Policy Simulation
* `POST /authorize/simulate`

#### Decision History
* `GET /decisions`
* `GET /decisions/{decision_id}`

#### Health Check
* `GET /health`