# API Key Management Service

## Responsibility
Issues and manages machine-to-machine credentials.

## Used By
* External integrations
* Microservices
* CI/CD pipelines
* Server-to-server communication

## APIs

### Manage Keys
* `POST   /api-keys`
* `GET    /api-keys`
* `GET    /api-keys/{key_id}`
* `DELETE /api-keys/{key_id}`

### Lifecycle Actions
* `POST   /api-keys/{key_id}/rotate`
* `POST   /api-keys/{key_id}/revoke`
* `POST   /api-keys/{key_id}/activate`
* `POST   /api-keys/{key_id}/deactivate`

### Observability & Analytics
* `GET    /api-keys/{key_id}/usage`
* `GET    /api-keys/{key_id}/audit`