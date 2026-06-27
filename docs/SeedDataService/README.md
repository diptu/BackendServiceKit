# Seed Data Service

## Objective

The **Seed Data Service** generates deterministic, production-like dummy data for local development, automated testing, demonstrations, and CI/CD environments. It allows every developer to work with a consistent and realistic dataset without affecting production systems.

---

# Goals

- Populate a fresh database with realistic data
- Support local development
- Support automated integration tests
- Provide demo data for UI development
- Enable repeatable CI/CD pipelines
- Generate deterministic datasets
- Reset environments quickly

---

# Functional Requirements

## Tenant Seeding

Generate multiple tenants.

Example:

- Alphabet
- Meta

Each tenant should contain:

- Organizations
- Users
- Roles
- Groups
- Policies
- Resources

---

## Organization Seeding

Each tenant should contain multiple organizations.

Example:

Alphabet

- Google Search
- YouTube
- DeepMind

Meta

- Facebook
- Instagram
- WhatsApp

---

## User Seeding

Generate users with realistic data.

Fields:

- UUID
- First Name
- Last Name
- Email
- Username
- Job Title
- Department
- Phone
- Status
- MFA Enabled
- Tenant
- Organization

Support configurable numbers of users.

Example

```
10 users

100 users

1000 users

10000 users
```

---

## Role Seeding

Generate system roles.

Minimum:

- Owner
- Admin
- Manager
- Member
- Auditor

Include role hierarchy.

---

## Permission Seeding

Generate permissions.

Examples

```
user:create
user:update
user:delete

organization:view

resource:create
resource:update
resource:delete

policy:view

audit:view
```

---

## Role Assignment

Automatically assign roles to users.

Distribution example

| Role | Percentage |
|-------|-----------:|
| Owner | 1% |
| Admin | 5% |
| Manager | 10% |
| Member | 80% |
| Auditor | 4% |

---

## Group Seeding

Generate groups.

Example

- AI Research
- Engineering
- Marketing
- Finance
- HR
- Security
- Operations

Assign users to groups.

---

## Resource Seeding

Generate realistic resources.

Examples

- Documents
- AI Models
- Policies
- Dashboards
- Reports
- APIs
- Storage Buckets

Each resource should include:

- Owner
- Organization
- Classification
- Created By
- Updated By
- Tags

---

## Resource Classifications

Generate classifications.

- Public
- Internal
- Confidential
- Restricted

---

## Policy Seeding

Generate RBAC and ABAC policies.

Examples

- MFA Required
- Corporate Network Only
- Business Hours
- Department Match
- Region Match
- Resource Classification

---

## Membership Seeding

Generate memberships.

Each user should belong to:

- Tenant
- Organization
- One or more Groups

---

## API Client Seeding

Generate service accounts.

Examples

- Backend API
- Mobile App
- CLI
- Internal Services

---

## Audit Log Seeding

Generate audit events.

Examples

- Login
- Logout
- Password Change
- User Created
- Resource Updated
- Policy Modified

---

## Security Event Seeding

Generate security events.

Examples

- MFA Failure
- Permission Denied
- Suspicious Login
- Token Revoked
- Rate Limit Triggered

---

## Environment Attribute Seeding

Generate ABAC environment attributes.

Examples

- Development
- Staging
- Production

Network

- Corporate
- VPN
- Public

Risk

- Low
- Medium
- High

---

## Deterministic Mode

Support deterministic generation.

Same seed value should always generate identical data.

Example

```bash
seed --seed 42
```

---

## Random Mode

Support random generation.

Example

```bash
seed --random
```

---

# Configuration

Support configuration file.

Example

```yaml
tenants: 2

organizations_per_tenant: 3

users_per_organization: 50

resources_per_organization: 200

groups_per_organization: 10

audit_logs: 5000

security_events: 500
```

---

# CLI Commands

Seed everything

```bash
make seed
```

Reset database

```bash
make reset-db
```

Reset and seed

```bash
make reseed
```

Seed one tenant

```bash
seed --tenant alphabet
```

Generate users

```bash
seed --users 1000
```

Generate resources

```bash
seed --resources 5000
```

Generate audit logs

```bash
seed --audit 100000
```

Generate security events

```bash
seed --security-events 5000
```

Deterministic generation

```bash
seed --seed 42
```

Random generation

```bash
seed --random
```

---

# Non-Functional Requirements

- Idempotent operations
- Fast execution
- Parallel generation where possible
- Configurable dataset sizes
- Memory efficient
- Transaction-safe
- Repeatable execution
- Extensible for new entity types

---

# Environment Support

Supported environments

- Local Development
- Docker
- CI/CD
- Automated Tests
- Demo Environment

Must never run automatically in Production.

---

# Recommended Project Structure

```text
seed_service/
├── cli.py
├── config.py
├── orchestrator.py
├── generators/
│   ├── tenant.py
│   ├── organization.py
│   ├── user.py
│   ├── role.py
│   ├── permission.py
│   ├── membership.py
│   ├── group.py
│   ├── resource.py
│   ├── policy.py
│   ├── api_client.py
│   ├── audit.py
│   └── security.py
├── faker/
├── utils/
└── fixtures/
```

---

# Success Criteria

The Seed Data Service should be able to:

- Create complete multi-tenant environments in a single command
- Generate realistic relationships between entities
- Produce deterministic datasets for testing
- Populate large datasets for performance testing
- Support frontend and backend development
- Enable automated integration and end-to-end testing
- Be easily extensible as new services are added to the platform
