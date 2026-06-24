# Tenant Management Service

## Purpose
The system of record for tenants. It stores and manages tenant metadata, configuration, status, settings, ownership, and relationships.

## Responsibilities
* Create tenant records
* Update tenant information
* Manage tenant settings
* Manage tenant owners
* Manage tenant metadata
* Tenant search and listing
* Tenant configuration management
* Tenant status visibility

## Owns
* Tenant entity
* Tenant settings
* Tenant profile
* Tenant metadata

## Example Database Tables
* `tenants`
* `tenant_settings`
* `tenant_contacts`
* `tenant_metadata`

## API Endpoints

### Tenants
* `POST   /tenants`
* `GET    /tenants`
* `GET    /tenants/{tenant_id}`
* `PATCH  /tenants/{tenant_id}`
* `DELETE /tenants/{tenant_id}`

### Settings
* `GET    /tenants/{tenant_id}/settings`
* `PATCH  /tenants/{tenant_id}/settings`

### Owners
* `GET    /tenants/{tenant_id}/owners`
* `POST   /tenants/{tenant_id}/owners`

### Metadata
* `GET    /tenants/{tenant_id}/metadata`
* `PATCH  /tenants/{tenant_id}/metadata`