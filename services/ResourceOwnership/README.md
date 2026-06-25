# Resource Ownership Service

## Responsibility

The Resource Ownership Service tracks and manages ownership relationships between resources and their owners.

Ownership information enables systems to determine who is responsible for a resource and is frequently used during authorization evaluation.

## Examples

Common ownership relationships may include:

```text id="h2r813"
Diptu owns Document A

Alice owns Project X

Bob owns Invoice Y
```

## Ownership Capabilities

The Resource Ownership Service provides:

* Ownership assignment
* Ownership lookup
* Ownership transfer
* Ownership lifecycle management
* Ownership metadata for authorization systems

## Important Notes

ABAC policies frequently depend on ownership information.

Example authorization rule:

```text id="v6m501"
ALLOW IF

resource.owner == user.id
```

The service stores ownership relationships only.

It does not perform authorization decisions itself.

## Ownership Model

An ownership record owns and manages the following attributes:

```text id="p7j426"
Ownership
├── Resource ID
├── Owner ID
└── Metadata
```

## Example Structure

Example ownership object:

```json id="z8x204"
{
  "resource_id": "doc_123",
  "owner_id": "user_100"
}
```

## API Endpoints

### Assign Ownership

```http id="r1k692"
POST /ownership
```

### Get Ownership Information

```http id="m9w830"
GET /ownership/{resource_id}
```

### Transfer Ownership

```http id="a5f481"
PATCH /ownership/{resource_id}
```

### Delete Ownership

```http id="g3u147"
DELETE /ownership/{resource_id}
```

## API Example

Assign ownership:

```json id="y4s629"
{
  "resource_id": "doc_123",
  "owner_id": "user_100"
}
```

## Ownership Relationships

```text id="n6t902"
Ownership
├── User
│   ├── Alice
│   ├── Bob
│   └── Diptu
└── Resource
    ├── Document
    ├── Project
    └── Invoice
```
