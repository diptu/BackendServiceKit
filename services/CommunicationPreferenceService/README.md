# Communication Preference Service

## Overview

The Communication Preference Service is responsible for storing and managing communication preferences for users and tenants.

It acts as the source of truth for determining whether specific communication channels or notification categories are permitted for a user.

Before sending any notification, the Notification Service queries this service to determine whether delivery is allowed.

---

## Responsibilities

The Communication Preference Service is responsible for:

* Storing user communication preferences
* Storing tenant-level communication preferences
* Managing channel opt-in and opt-out settings
* Managing notification category permissions
* Managing preferred languages
* Providing preference lookup APIs
* Acting as a policy data source for notification systems

---

## Questions It Answers

The service answers questions such as:

* Can this user receive marketing emails?
* Can this user receive SMS messages?
* Can this user receive security alerts?
* Can this user receive push notifications?
* What language does the user prefer?

---

## Non-Responsibilities

The Communication Preference Service should **not**:

* Send notifications
* Trigger business workflows
* Decide what notifications should be generated
* Deliver SMS, Email, or Push messages
* Apply notification routing logic

These responsibilities belong to other services.

---

## Example User Preferences

```json id="pref011"
{
  "email": true,
  "sms": false,
  "push": true,
  "marketing": false,
  "security_alerts": true,
  "language": "en"
}
```

---

## Example Integration Flow

Before sending a notification:

```text id="flow311"
Incoming Event
      │
      ▼
Notification Service
      │
      ▼
Communication Preference Service
      │
      ▼
Preference Evaluation
      │
      ▼
Allowed Channels Returned
      │
      ▼
SMS / Email / Push Services
```

---

## Common Use Cases

Examples:

* User disables marketing emails
* User opts out of SMS notifications
* User enables push notifications
* User selects preferred language
* Tenant enforces communication policies

---

# API Endpoints

## User Preference APIs

### Get User Preferences

```http id="usr123"
GET /users/{user_id}/preferences
```

Retrieve communication preferences for a user.

---

### Replace User Preferences

```http id="usr331"
PUT /users/{user_id}/preferences
```

Replace all user preference settings.

---

### Update User Preferences

```http id="usr412"
PATCH /users/{user_id}/preferences
```

Partially update communication preferences.

---

## Tenant Preference APIs

### Get Tenant Preferences

```http id="ten114"
GET /tenants/{tenant_id}/preferences
```

Retrieve tenant-level communication preferences.

---

### Update Tenant Preferences

```http id="ten502"
PUT /tenants/{tenant_id}/preferences
```

Replace tenant communication settings.

---

## Preference Management APIs

### Opt In

```http id="opt100"
POST /preferences/opt-in
```

Enable a communication channel or category.

---

### Opt Out

```http id="opt401"
POST /preferences/opt-out
```

Disable a communication channel or category.

---

### Get Available Channels

```http id="chn299"
GET /preferences/channels
```

Retrieve supported communication channels.

Examples:

* Email
* SMS
* Push

---

### Get Supported Languages

```http id="lng811"
GET /preferences/languages
```

Retrieve supported language options.

Examples:

* en
* fr
* es
* bn

---

## High-Level Architecture

```text id="arch551"
Notification Service
        │
        ▼
Communication Preference Service
        │
 ┌──────┴─────────┐
 ▼                ▼
User Preferences  Tenant Preferences
```

---

## Decision Flow

```text id="flow992"
Notification Request
         │
         ▼
Check User Preferences
         │
         ▼
Evaluate Allowed Channels
         │
         ▼
Return Permission Result
```

---

## Design Principle

The Communication Preference Service should remain a policy data service:

**Store → Query → Return**

Decision-making and message delivery should remain outside the service boundary.
