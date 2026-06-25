# Resource Sharing Service

## Responsibility

The Resource Sharing Service manages access granted to resources beyond their original ownership.

Its purpose is to provide controlled access to resources while preserving the original owner.

This service answers questions such as:

* Who has been granted access?
* What access was granted?
* Who owns the resource?

## Example

Consider the following scenario:

```text id="s5p209"
Diptu owns document

Diptu shares document with Alice

Alice can view document
```

Ownership remains:

```text id="x2r410"
Diptu
```

Access granted:

```text id="a9w621"
Alice
```

## Resource Sharing Capabilities

The Resource Sharing Service provides:

* Resource sharing
* Shared access tracking
* Permission assignment
* Shared access updates
* Shared access removal

## Ownership Model

A shared resource relationship owns and manages:

```text id="v3n702"
Share
├── Resource
├── Shared User
├── Permission
└── Metadata
```

## Example Structure

Example sharing object:

```json id="c8m104"
{
  "resource_id": "doc_123",
  "shared_with": "user_200",
  "permission": "read"
}
```

## API Endpoints

### Share Resource

```http id="k7u801"
POST /shares
```

### Get Resource Shares

```http id="q5d620"
GET /shares/{resource_id}
```

### Update Share

```http id="w2p138"
PATCH /shares/{share_id}
```

### Remove Share

```http id="n6r524"
DELETE /shares/{share_id}
```

### User Shared Resources

```http id="t8f413"
GET /users/{user_id}/shared-resources
```

## API Example

Create a resource share:

```json id="j1x790"
{
  "resource_id": "doc_123",
  "shared_with": "user_200",
  "permission": "read"
}
```

## Resource Sharing Relationships

```text id="g4e216"
Resource Owner
│
├── Owns Resource
│
└── Share
    ├── Shared User
    └── Permission
```

## Important Notes

Resource sharing does not transfer ownership.

Ownership and shared access are separate concepts:

* Owners retain full ownership rights
* Shared users receive delegated access
* Shared permissions may be modified or revoked
* Multiple users may receive independent access levels
