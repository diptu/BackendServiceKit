# Creating a Tenant (and its Owner) — API Flow

This walks through provisioning a new tenant end-to-end, including how to get
past the two requirements that look circular at first:

- `POST /api/v1/tenants` requires an **`owner_id`** (a User Service `user_id`).
- `POST /api/v1/users` requires an **`X-Tenant-ID`** header.

The chicken-and-egg is only apparent. This doc explains why, and gives a
copy-pasteable flow.

---

## TL;DR

1. **Create the tenant first**, with any UUID as `owner_id` (it is *not*
   validated — see [Why `owner_id` isn't a blocker](#why-owner_id-isnt-a-blocker)).
   The response gives you the tenant `id` → call it `T`.
2. **Create the owner user** with `X-Tenant-ID: T`. The header value you were
   missing is simply the tenant id from step 1. The response gives you the user
   `id` → call it `U`.
3. **Register `U` as the tenant owner** via `POST /api/v1/tenants/{T}/owners`.
4. (Optional) **Drive the tenant to `active`** through the lifecycle endpoints.

---

## Services & ports

| Service | Port | Base path |
|---|---|---|
| **Tenent** | 8005 | `/api/v1/tenants`, `/api/v1/lifecycle` |
| **User**   | 8023 | `/api/v1/users` |
| **APIGateway** | 8080 | proxies both; injects `X-Tenant-ID` from the JWT |

> **Direct vs. gateway:** In production, requests go through the APIGateway,
> which verifies the caller's JWT and **overrides `X-Tenant-ID`** from the
> verified token claim — a service never trusts a client-supplied header except
> from the gateway. The manual `X-Tenant-ID` below is for calling the services
> **directly** in local/dev.

---

## Why `owner_id` isn't a blocker

In `services/Tenent/app/models/tenant.py`, `owner_id` is a plain projection
column — **not** a foreign key to the User Service:

```python
owner_id: Mapped[UUID] = mapped_column(
    nullable=False,
    comment="Primary owner user_id (projection — not a FK to User Service).",
)
```

Tenant creation stores it and seeds a `TenantContact(role=OWNER)`. There is
**no synchronous call to the User Service to validate it exists**. So you can
create the tenant before the owner user exists, then reconcile.

## Why `X-Tenant-ID` isn't a blocker

The User Service reads `X-Tenant-ID` in two different ways depending on
`siloed_multitenancy_enabled` (`services/User/app/core/config.py`, default
`False`):

| Mode | What `X-Tenant-ID` does | Does the tenant DB need to exist first? |
|---|---|---|
| **Shared-schema** (default, `siloed_multitenancy_enabled=False`) | Stamps the `tenant_id` column and scopes email-uniqueness. Data goes to the single shared `DATABASE_URL`. | **No.** Any tenant UUID works. |
| **Siloed** (`siloed_multitenancy_enabled=True`) | Also routes the write to that tenant's **own physical database**, resolved from the header. Fails closed if the header is absent. | **Yes** — see [Siloed mode](#siloed-mode-database-per-tenant). |

In the default shared-schema mode there is nothing extra to set up: the header
value is just the tenant id you created in step 1.

---

## Step-by-step (shared-schema / default local dev)

### 1. Create the tenant

```bash
OWNER_PLACEHOLDER=$(uuidgen | tr 'A-Z' 'a-z')

curl -s -X POST http://localhost:8005/api/v1/tenants \
  -H 'Content-Type: application/json' \
  -d "{
    \"name\": \"acme-corp\",
    \"display_name\": \"Acme Corp\",
    \"region\": \"us-east-1\",
    \"owner_id\": \"$OWNER_PLACEHOLDER\"
  }"
```

Response (tenant starts in `draft`):

```json
{ "id": "T-uuid", "name": "acme-corp", "status": "draft", "owner_id": "...", ... }
```

Grab `id` → this is **`T`**.

### 2. Create the owner user (the header value is `T`)

```bash
T="<tenant id from step 1>"

curl -s -X POST http://localhost:8023/api/v1/users \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: $T" \
  -d '{
    "email": "owner@acme.com",
    "first_name": "Ada",
    "last_name": "Owner"
  }'
```

Response (user starts in `pending`):

```json
{ "id": "U-uuid", "tenant_id": "T-uuid", "email": "owner@acme.com", "status": "pending", ... }
```

Grab `id` → this is **`U`**.

### 3. Register the real owner on the tenant

```bash
U="<user id from step 2>"

curl -s -X POST http://localhost:8005/api/v1/tenants/$T/owners \
  -H 'Content-Type: application/json' \
  -d "{ \"user_id\": \"$U\", \"role\": \"owner\" }"
```

### 4. (Optional) Drive the tenant to `active`

Transitions are explicit (compliance gates — not auto-advanced):

```bash
curl -s -X PUT http://localhost:8005/api/v1/lifecycle/$T/provision
curl -s -X PUT http://localhost:8005/api/v1/lifecycle/$T/pend
curl -s -X PUT http://localhost:8005/api/v1/lifecycle/$T/activate
```

`draft → provisioning → pending → active`.

---

## Known gap: the initial `owner_id` can't be re-pointed

`UpdateTenantRequest` does **not** include `owner_id`, so the primary owner set
at creation cannot be changed through the API. The `/tenants/{id}/owners`
sub-resource only **adds/removes additional** owner contacts. Consequences:

- The placeholder `owner_id` from step 1 stays on the tenant row even after you
  register the real user `U` as an owner contact in step 3.
- If you need `tenant.owner_id == U` exactly, you must know `U` before creating
  the tenant. That's only possible by creating the user under an
  **already-existing** tenant (e.g. a bootstrap/platform tenant) and passing
  that user's id as `owner_id` for the *new* tenant.

For most local/testing purposes the placeholder is harmless; flag this if you
build the real platform-onboarding flow.

---

## Siloed mode (database-per-tenant)

Only relevant when `siloed_multitenancy_enabled=True`. Then step 2's
`X-Tenant-ID: T` routes the write to tenant `T`'s **own** database, which must
exist and be migrated first. Set these on the User service:

```bash
SILOED_MULTITENANCY_ENABLED=true
TENANT_RESOLVER=template
# {tenant_id} is substituted per request:
TENANT_DATABASE_URL_TEMPLATE=postgresql+asyncpg://postgres:postgres@localhost:5433/tenant_{tenant_id}
```

Provision + migrate `T`'s database before creating users in it:

```bash
cd services/User
uv run python -m scripts.tenant_migrations provision "$T"
```

For a single local database, point every tenant at one DB with an override
instead of a template:

```bash
TENANT_DATABASE_OVERRIDES='{"T-uuid":"postgresql+asyncpg://postgres:postgres@localhost:5433/nutratenant_user"}'
```

---

## Sequence

```mermaid
sequenceDiagram
    actor Op as Operator / bootstrap
    participant TN as Tenent (8005)
    participant US as User (8023)

    Op->>TN: POST /api/v1/tenants  {owner_id: <placeholder uuid>}
    TN-->>Op: 201 {id: T, status: draft}
    Op->>US: POST /api/v1/users  (X-Tenant-ID: T) {email,...}
    US-->>Op: 201 {id: U, tenant_id: T, status: pending}
    Op->>TN: POST /api/v1/tenants/T/owners  {user_id: U, role: owner}
    TN-->>Op: 201 {owner registered}
    opt drive to active
        Op->>TN: PUT /api/v1/lifecycle/T/provision
        Op->>TN: PUT /api/v1/lifecycle/T/pend
        Op->>TN: PUT /api/v1/lifecycle/T/activate
    end
```
