# 🚀 Backend Service Kit

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Latest-green?style=flat-square" alt="FastAPI">
  <img src="https://img.shields.io/badge/Architecture-Production--Ready-orange?style=flat-square" alt="Architecture">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
</p>

### Reusable, production-grade microservices and cloud-native patterns built with FastAPI.

**Backend Service Kit** is a modular reference architecture designed to solve common distributed system problems. It serves as a plug-and-play laboratory for building scalable, secure, and observable backend platforms.

---

## 🏗️ Core Roadmap & Services

Seven services are implemented and independently tested (Python/FastAPI —
run `make test SERVICE=<Name>` from the repo root, or see each service's
own `TODO.md` for what was built and why). Everything else below that is
still the original design-doc/roadmap vision.

| Service | Status | Core Architecture Highlights |
| :--- | :--- | :--- |
| **🔐 IAM** | ✅ Active | RBAC, ABAC policy evaluation engine, groups, entitlements, access reviews |
| **🔑 Authentication** | ✅ Active | JWT (HS256/RS256) access tokens, rotating/revocable refresh tokens, credential storage, account lockout, MFA (TOTP), OAuth 2.1 (auth-code + PKCE), OIDC SSO — WebAuthn/SAML not yet built |
| **🚀 API Gateway** | ✅ Active | Reverse proxy, Redis cache, Kong integration, gateway-verified JWT auth boundary |
| **🏢 Tenent** | ✅ Active | Merged Tenant Management + Lifecycle + Isolation |
| **🏬 Organization Management** | ✅ Active | Org hierarchy, teams, invitations |
| **👤 User** | ✅ Active | Merged User Management + Lifecycle + Profile |
| **📡 Observability Management** | ✅ Active | Merged Logging/Tracing/Metrics/Monitoring/Alerting/Health |
| **🔔 Notification** | 🚧 Planned | Event-driven Email, SMS, & Push notification workers |
| **💳 Payment** | 🚧 Planned | Stripe/Idempotent billing & transaction pipelines |
| **📂 File Storage** | 🚧 Planned | S3-compatible Object Storage & secure CDN streaming |
| **🔎 Search** | 🚧 Planned | Full-text indexing, vector search, & sync pipelines |
| **⏰ Scheduler** | 🚧 Planned | Distributed background jobs & workflow orchestration |
| **📊 Analytics** | 🚧 Planned | Real-time event tracking, clickstream data ingestion |
| **📝 Audit Log** | 🚧 Planned | Immutable activity & compliance ledger |
| **🚩 Feature Flags** | 🚧 Planned | Dynamic variant evaluation & runtime toggles |

---

## 🛠️ Unified Ecosystem & Stack

```
┌────────────────────────────────────────────────────────────────────────┐
│                        🚀 API Gateway (JWT + Rate Limiting)            │
└───────┬────────────────────────────────┬───────────────────────┬───────┘
        │                                │                       │
 🔐 IAM Service               🔔 Notification Service     💳 Payment Service
        │                                │                       │
┌───────┴────────────────────────────────┴───────────────────────┴───────┐
│              🔄 Event-Driven Backbone (Kafka / RabbitMQ)               │
└────────────────────────────────────────────────────────────────────────┘
```

* **Runtime & Framework:** Python 3.12+, FastAPI (Asynchronous ASGI)
* **Data & Caching:** PostgreSQL (Relational), Redis (Caching & Rate Limiting)
* **Messaging:** Kafka / RabbitMQ (Event-Driven Architecture)
* **Infrastructure:** Docker, Kubernetes, GitHub Actions (Per-service CI/CD pipelines)
* **Observability:** OpenTelemetry, Prometheus, Grafana, Loki (Structured logging & tracing)

---

## 📂 Repository Structure

```text
backend-service-kit/
├── services/             # Independent microservices
│   ├── iam/              # Each service has its own src, tests, and Dockerfile
│   └── notification/
├── shared/               # Shared libraries (middleware, loggers, schemas)
├── infrastructure/       # K8s manifests, Docker Compose, API Gateway configs
└── .github/workflows/    # Service-isolated CI/CD pipelines
```

---

## 🎯 Engineering & Design Principles

* **Domain-Driven Design (DDD):** Strict separation of concerns and bounded contexts.
* **Twelve-Factor & Cloud-Native:** Stateless design, environment-isolated configuration, and graceful degradation.
* **Zero-Trust Security:** Built-in secure communication defaults, perimeter API Gateway validation, and mTLS.
* **Observability-First:** Distributed tracing injected across network boundaries via OpenTelemetry.

---

## 🏛️ Core Architectural Pillars *(Target)*

> [!NOTE]
> **This describes the north-star multi-tenancy model — it is not yet
> implemented.** The current build isolates tenants with **shared-schema**
> multi-tenancy: every service owns a single database and scopes every query
> by a required `tenant_id` column (e.g. the composite index `(tenant_id,
> email)`), with the tenant identity resolved from a **gateway-verified JWT
> claim** and forwarded as the `X-Tenant-ID` header — not from a subdomain.
> The two pillars below are the direction the platform is designed to grow
> toward, captured here so the target and the current state don't drift.

### 1. Siloed Multi-tenancy (Data Layer)

The **database-per-tenant** model. Unlike shared-schema multi-tenancy (where
all tenants coexist in one table behind a `tenant_id` column — what this repo
does today), this approach provides total logical separation.

* **Pros:** Maximum security, simplified compliance (GDPR/HIPAA), and the
  ability to restore a specific tenant's data without affecting others.
* **Cons:** Higher infrastructure overhead and real complexity in managing
  schema migrations across hundreds or thousands of databases.

### 2. Subdomain Routing (Access Layer)

Using subdomains (e.g. `meta.my-site.com`) as the primary tenant identifier —
a standard pattern for a personalized, per-tenant experience.

* **Mechanism:** A **Tenant Resolver** middleware extracts the subdomain from
  the incoming request `Host` header, queries a central **Control Plane
  Database** to resolve that subdomain to a specific database connection
  string, and dynamically swaps the connection context for the duration of
  the request.

#### Conceptual Architecture

```text
  meta.my-site.com                 acme.my-site.com
        │                                │
        ▼                                ▼
┌────────────────────────────────────────────────────┐
│   🚀 API Gateway  +  Tenant Resolver middleware     │
│   (extract subdomain from Host header)              │
└───────────────────────┬────────────────────────────┘
                        │  subdomain
                        ▼
              ┌───────────────────────┐
              │  🗺️ Control Plane DB   │  subdomain → {host, port, creds}
              └───────────┬───────────┘
                        │  connection string
                        ▼
              ┌───────────────────────┐
              │  🐘 PgBouncer (pool)   │
              └───┬───────┬───────┬───┘
                  ▼       ▼       ▼
              ┌──────┐┌──────┐┌──────┐
              │ DB:  ││ DB:  ││ DB:  │   one isolated database per tenant
              │ meta ││ acme ││  …   │
              └──────┘└──────┘└──────┘
```

#### Technical Considerations for Implementation

To operate this at an enterprise level, engineers typically implement:

* **The Control Plane:** A lightweight, central database mapping
  subdomains/tenants to connection details (host, port, credentials).
* **Connection Pooling Strategy:** Hundreds of open connections will exhaust
  a database server's memory — front them with a specialized connection
  proxy (**PgBouncer** for PostgreSQL) to pool connections efficiently.
* **Migration Orchestrator:** Never run migrations by hand. Build an
  automated "flight control" script that iterates the tenant database list
  and applies DDL changes during deployments.
* **Tenant Identity Context:** Ensure the auth layer (JWTs/session tokens)
  encodes the `tenant_id`, so a user can't force-access another tenant's
  subdomain by spoofing the URL. *(This one already holds today — the
  gateway verifies the JWT and overrides any client-supplied `X-Tenant-ID`
  with the verified claim.)*

---


## 📋 Service List — curated for Siloed Multi-tenancy

The platform is scoped to **16 services** that together form the siloed
(database-per-tenant) multi-tenant architecture (see "Core Architectural
Pillars" above). Eight are implemented; the rest are the pieces that turn the
opt-in siloing plumbing into a live database-per-tenant deployment.

| # | Service | Status | Role in Siloed multi-tenancy |
| :-- | :-- | :-- | :-- |
| 1 | **IAM** | ✅ Active | RBAC + ABAC policy engine; per-tenant database in siloed mode |
| 2 | **Authentication** | ✅ Active | Credentials, JWT (HS256/RS256), MFA, OAuth 2.1, OIDC SSO — siloed per tenant |
| 3 | **User** | ✅ Active | Identity CRUD, profile, lifecycle — siloed per tenant |
| 4 | **Session Management** | ✅ Active | Session/device tracking, force-logout — siloed per tenant |
| 5 | **Tenent** (Mgmt + Lifecycle + Isolation + **Control Plane**) | ✅ Active | Owns the global tenant → database registry + subdomain map that makes siloing possible |
| 6 | **Organization Management** | ✅ Active | Org/workspace/team hierarchy — siloed per tenant |
| 7 | **API Gateway** (Tenant Resolver) | ✅ Active | Resolves subdomain → tenant, enforces the tenant boundary, forwards the authoritative `X-Tenant-ID` |
| 8 | **Observability Management** | ✅ Active | Deliberate **exception** — telemetry stays pooled with a `tenant_id` label, *not* siloed |
| 9 | **Tenant Provisioning** | 🚧 Planned | Physical `CREATE DATABASE` + run every service's migrations when a tenant is provisioned |
| 10 | **Secrets & Key Management** | 🚧 Planned | Holds the per-tenant DB credentials the Control Plane references (Vault/KMS) |
| 11 | **Migration Orchestrator** | 🚧 Planned | Applies DDL across all N tenant databases on deploy (per-service `tenant_migrations.py` today) |
| 12 | **Notification** | 🚧 Planned | Delivers password-reset / invite links out-of-band (Authentication depends on it) |
| 13 | **Audit & Compliance Logging** | 🚧 Planned | Immutable per-tenant activity ledger — a compliance *pro* of siloing (GDPR/HIPAA) |
| 14 | **File & Object Storage** | 🚧 Planned | S3-compatible per-tenant file/object storage — isolated buckets/prefixes per tenant, mirroring the DB-per-tenant boundary |
| 15 | **SSO / Identity Federation** | 🚧 Planned | External IdP (SAML/OIDC) federation mapped to local tenant identities |
| 16 | **Billing & Subscription** | 🚧 Planned | Multi-tenant SaaS metering, plans, invoicing |

## 🤝 Contributing & License

Contributions, architectural issues, and feature discussions are highly encouraged. Distributed under the **MIT License**.

<p align="center">
  <b>Building reusable systems, one module at a time.</b><br>
  ⭐ Star this repository to support the project!
</p>

