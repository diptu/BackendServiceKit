# User Profile Service

## Purpose
Stores profile information about users.

This service contains user metadata, not identity or access data.

### Question it answers
* What information is associated with this user?

## Responsibilities
* Personal details
* Avatar management
* Contact information
* Preferences
* Locale settings
* Timezone settings

## Owns
* `user_profiles`
* `user_preferences`
* `avatars`
* `contact_info`

## Example
```json
{
  "first_name": "Nazmul",
  "last_name": "Diptu",
  "timezone": "Asia/Dhaka",
  "language": "en"
}
```
API Endpoints
Profile
```bash
GET   /profiles/{user_id}

PATCH /profiles/{user_id}

Avatar
POST   /profiles/{user_id}/avatar

DELETE /profiles/{user_id}/avatar

Preferences
GET   /profiles/{user_id}/preferences

PATCH /profiles/{user_id}/preferences

Contact Information
GET   /profiles/{user_id}/contacts

PATCH /profiles/{user_id}/contacts
```