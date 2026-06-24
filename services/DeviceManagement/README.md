# Device Management Service

## Responsibility
Tracks devices that access the platform.

## Scope
* Trusted devices
* Registered devices
* Device fingerprinting
* Device approval
* Device revocation

## Examples
* MacBook
* iPhone
* Android
* Windows PC

## APIs

### Devices
* `POST   /devices/register`
* `GET    /devices`
* `GET    /devices/{device_id}`
* `PATCH  /devices/{device_id}`
* `DELETE /devices/{device_id}`

### Device Trust & Approval
* `POST   /devices/{device_id}/trust`
* `POST   /devices/{device_id}/untrust`
* `POST   /devices/{device_id}/approve`
* `POST   /devices/{device_id}/revoke`

### User Devices
* `GET    /users/{user_id}/devices`