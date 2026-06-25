# Resource Registry Service

## Responsibility

The Resource Registry Service acts as the central catalog for every protected object within the platform.

It provides a single source of truth for resource discovery, metadata, and ownership context.

Without a centralized resource registry, authorization models such as ABAC cannot effectively evaluate access decisions.

Think of this service as an:

**Asset Inventory Service**

## Examples

Common resources within the platform may include:

```text id="u2r615"
Document
Invoice
Workspace
Project
Dataset
Report
API Key
```

## Resource Registry Capabilities

The Resource Registry Service provides:

* Centralized resource registration
* Resource metadata management
* Resource discovery and lookup
* Ownership and tenant association
* Resource inventory for authorization systems

## Important Notes

Without this service:

* ABAC cannot evaluate access conditions consistently
* Resource ownership becomes fragmented across services
* Cross-service resource discovery becomes difficult

The service acts only as a registry and metadata catalog.

It does not implement authorization decisions.

## Ownership Model

A resource entry owns and manages the following attributes:

```text id="w4f207"
Resource
├── Resource ID
├── Resource Type
├── Tenant ID
└── Metadata
```

## Example Structure

Example resource object:

```json id="d9n318"
{
  "resource_id": "doc_123",
  "resource_type": "document",
  "tenant_id": "tenant_1"
}
```

## API Endpoints

### Register Resource

```http id="q1k802"
POST /resources
```

### Get Resource

```http id="b6z540"
GET /resources/{resource_id}
```

### Search Resources

```http id="x7m124"
GET /resources
```

### Update Resource Metadata

```http id="e3h617"
PATCH /resources/{resource_id}
```

### Delete Resource

```http id="n0v489"
DELETE /resources/{resource_id}
```

## API Example

Register a new resource:

```json id="r8s291"
{
  "resource_type": "document",
  "resource_id": "doc_123"
}
```

## Resource Relationships

```text id="p5j764"
Resource Registry
├── Documents
├── Invoices
├── Workspaces
├── Projects
├── Datasets
├── Reports
└── API Keys
```
