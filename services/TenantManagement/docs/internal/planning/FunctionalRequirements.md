# Functional Requirements

**Service:** Tenant Management Service

**Version:** 1.0

**Status:** Draft

---

# 1. Overview

The Tenant Management Service is the **system of record** for tenant information within the SaaS platform.

It is responsible for storing and managing tenant master data, including tenant profile, settings, metadata, ownership, and configuration.

This service does **not** provision infrastructure, manage subscriptions, or handle tenant lifecycle automation. Those responsibilities belong to dedicated services.

---

# 2. Functional Requirements

## FR-001 Create Tenant

### Description

The system shall allow authorized platform administrators to create a tenant record.

### Inputs

* Tenant Name
* Display Name
* Tenant Slug
* Primary Owner
* Contact Information
* Timezone
* Locale
* Currency
* Region
* Initial Settings
* Initial Metadata

### Outputs

* Tenant ID
* Tenant Status
* Created Timestamp

### Validation

* Tenant name must be unique.
* Tenant slug must be unique.
* Required fields must be provided.

---

## FR-002 Retrieve Tenant

The system shall retrieve tenant information by:

* Tenant ID
* Tenant Slug

The response shall include:

* Tenant Profile
* Settings
* Metadata
* Owners
* Current Status

---

## FR-003 List Tenants

The system shall list tenants.

Supported capabilities:

* Pagination
* Filtering
* Sorting
* Search

---

## FR-004 Update Tenant

Authorized administrators shall update:

* Display Name
* Contact Information
* Description
* Region
* Timezone
* Locale
* Currency

Immutable fields include:

* Tenant ID
* Created Timestamp

---

## FR-005 Delete Tenant

The system shall support soft deletion of tenant records.

Deletion shall not permanently remove historical information.

---

## FR-006 Manage Tenant Settings

The system shall manage tenant-specific settings.

Supported settings include:

* Timezone
* Locale
* Language
* Currency
* Date Format
* Number Format
* Session Timeout
* Default Theme

---

## FR-007 Retrieve Tenant Settings

The system shall retrieve all tenant settings.

---

## FR-008 Update Tenant Settings

Authorized users shall update tenant settings.

Setting updates shall be versioned and audited.

---

## FR-009 Manage Tenant Owners

The system shall maintain tenant ownership information.

Supported operations:

* Add Owner
* Remove Owner
* Update Owner
* List Owners

Each tenant shall have at least one active owner.

---

## FR-010 Retrieve Tenant Owners

The system shall retrieve all tenant owners.

---

## FR-011 Manage Tenant Metadata

The system shall store extensible metadata as key-value pairs.

Examples include:

* Industry
* Company Size
* Customer Tier
* Business Category
* Internal Notes

---

## FR-012 Retrieve Tenant Metadata

The system shall retrieve tenant metadata.

---

## FR-013 Update Tenant Metadata

Authorized users shall update tenant metadata.

Metadata updates shall not require database schema changes.

---

## FR-014 Search Tenants

Support searching by:

* Tenant Name
* Tenant Slug
* Owner
* Region
* Metadata

---

## FR-015 Filter Tenants

Support filtering by:

* Status
* Region
* Locale
* Currency
* Created Date
* Updated Date

---

## FR-016 Sort Tenants

Support sorting by:

* Name
* Created Date
* Updated Date

Ascending and descending order shall be supported.

---

## FR-017 Pagination

Support configurable pagination.

Recommended:

* Cursor Pagination

Optional:

* Offset Pagination

---

## FR-018 Validation

Validate:

* Duplicate tenant names
* Duplicate slugs
* Invalid locale
* Invalid timezone
* Invalid region
* Invalid currency

---

## FR-019 Audit Logging

The following operations shall generate audit events:

* Create Tenant
* Update Tenant
* Delete Tenant
* Update Settings
* Update Metadata
* Add Owner
* Remove Owner
* Update Owner

---

## FR-020 Event Publishing

Publish domain events including:

* TenantCreated
* TenantUpdated
* TenantDeleted
* TenantSettingsUpdated
* TenantMetadataUpdated
* TenantOwnerAdded
* TenantOwnerRemoved
* TenantOwnerUpdated

---

## FR-021 Event Consumption

Consume events from other services when tenant data requires synchronization.

Examples include:

* TenantProvisioned
* TenantOnboarded
* TenantMigrated
* SubscriptionActivated

---

## FR-022 Authorization

Only authorized platform administrators may:

* Create tenants
* Delete tenants
* Modify tenant owners
* Update settings
* Update metadata

---

## FR-023 Tenant Isolation

The service shall ensure tenant records are isolated and cannot be accessed across tenant boundaries except by authorized platform administrators.

---

## FR-024 Health Endpoint

The service shall expose:

* Liveness endpoint
* Readiness endpoint

---

## FR-025 Metrics

Expose operational metrics including:

* Total Tenants
* Active Tenants
* Deleted Tenants
* Request Count
* Error Count
* API Latency

---

# 3. Owned Resources

The Tenant Management Service owns the following resources:

* Tenant
* Tenant Settings
* Tenant Profile
* Tenant Contacts
* Tenant Metadata

---

# 4. Database Tables

The service owns the following database tables:

* `tenants`
* `tenant_settings`
* `tenant_contacts`
* `tenant_metadata`

---

# 5. REST API Endpoints

## Tenant Management

| Method | Endpoint               | Description        |
| ------ | ---------------------- | ------------------ |
| POST   | `/tenants`             | Create tenant      |
| GET    | `/tenants`             | List tenants       |
| GET    | `/tenants/{tenant_id}` | Retrieve tenant    |
| PATCH  | `/tenants/{tenant_id}` | Update tenant      |
| DELETE | `/tenants/{tenant_id}` | Soft delete tenant |

---

## Tenant Settings

| Method | Endpoint                        | Description       |
| ------ | ------------------------------- | ----------------- |
| GET    | `/tenants/{tenant_id}/settings` | Retrieve settings |
| PATCH  | `/tenants/{tenant_id}/settings` | Update settings   |

---

## Tenant Owners

| Method | Endpoint                                 | Description  |
| ------ | ---------------------------------------- | ------------ |
| GET    | `/tenants/{tenant_id}/owners`            | List owners  |
| POST   | `/tenants/{tenant_id}/owners`            | Add owner    |
| PATCH  | `/tenants/{tenant_id}/owners/{owner_id}` | Update owner |
| DELETE | `/tenants/{tenant_id}/owners/{owner_id}` | Remove owner |

---

## Tenant Metadata

| Method | Endpoint                        | Description       |
| ------ | ------------------------------- | ----------------- |
| GET    | `/tenants/{tenant_id}/metadata` | Retrieve metadata |
| PATCH  | `/tenants/{tenant_id}/metadata` | Update metadata   |
