# Template Management Service

## Overview

The Template Management Service is responsible for storing and managing reusable communication templates across different channels.

It acts as the centralized repository for message content and allows downstream systems to retrieve, render, version, and manage templates.

The Notification Service queries this service whenever it needs message content.

Example:

Request:

```text id="rq101"
PASSWORD_RESET
```

Response:

```text id="rs202"
Hello {{first_name}}

Your password has been changed.
```

---

## Responsibilities

The Template Management Service is responsible for:

* Storing reusable templates
* Managing template versions
* Rendering templates with variables
* Supporting template preview functionality
* Publishing and archiving templates
* Organizing templates by categories
* Supporting multiple communication channels

---

## Non-Responsibilities

The Template Management Service should **not**:

* Send messages
* Determine notification policies
* Decide notification channels
* Trigger workflows
* Manage delivery providers

These responsibilities belong to downstream systems.

---

## Supported Channels

The service supports templates for:

* Email
* SMS
* Push
* In-app

---

## Common Templates

Examples:

* PASSWORD_RESET
* EMAIL_VERIFICATION
* NEW_LOGIN_ALERT
* INVOICE_CREATED
* MFA_ENABLED

---

## Example Template Structure

```json id="tmp001"
{
  "template_code": "PASSWORD_RESET",
  "channel": "email",
  "subject": "Password Updated",
  "body": "Hello {{first_name}}\n\nYour password has been changed.",
  "version": 3,
  "status": "published"
}
```

---

## Example Flow

```text id="flow111"
Incoming Event
      │
      ▼
Notification Service
      │
      ▼
Request Template:
PASSWORD_RESET
      │
      ▼
Template Management Service
      │
      ▼
Return Template Content
      │
      ▼
Notification Service
```

---

# API Endpoints

## Template Management APIs

### Create Template

```http id="tmp120"
POST /templates
```

Create a new template.

---

### Get Templates

```http id="tmp121"
GET /templates
```

Retrieve available templates.

---

### Get Template Details

```http id="tmp122"
GET /templates/{template_id}
```

Retrieve template details.

---

### Update Template

```http id="tmp123"
PUT /templates/{template_id}
```

Replace template content.

---

### Delete Template

```http id="tmp124"
DELETE /templates/{template_id}
```

Remove a template.

---

## Template Operations APIs

### Preview Template

```http id="tmp125"
POST /templates/{template_id}/preview
```

Preview rendered output before publishing.

---

### Render Template

```http id="tmp126"
POST /templates/{template_id}/render
```

Render a template using provided variables.

Example variables:

```json id="render001"
{
   "first_name": "John"
}
```

---

### Publish Template

```http id="tmp127"
POST /templates/{template_id}/publish
```

Make a template available for production use.

---

### Archive Template

```http id="tmp128"
POST /templates/{template_id}/archive
```

Move a template into archived state.

---

## Metadata APIs

### Get Template Categories

```http id="tmp129"
GET /template-categories
```

Retrieve supported template categories.

Examples:

* Authentication
* Billing
* Marketing
* Security
* System

---

### Get Template Versions

```http id="tmp130"
GET /template-versions
```

Retrieve version history.

---

## High-Level Architecture

```text id="arch100"

                     ┌─────────────────────┐
                     │ Notification Service │
                     └──────────┬──────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼

     ┌────────────────┐ ┌───────────────┐ ┌────────────────┐
     │ Email Service  │ │ SMS Service   │ │ Push Service   │
     └────────────────┘ └───────────────┘ └────────────────┘

                ▲
                │

     ┌──────────────────────────┐
     │ Communication Preference │
     └──────────────────────────┘

                ▲
                │

     ┌──────────────────────────┐
     │ Template Management      │
     └──────────────────────────┘
```

---

## Template Resolution Flow

```text id="flow888"
Notification Request
          │
          ▼
Notification Service
          │
          ▼
Template Management Service
          │
          ├── Find Template
          ├── Apply Variables
          ├── Select Version
          ▼
Rendered Content
```

---

## Design Principle

The Template Management Service should remain a content management service:

**Store → Render → Return**

Delivery, orchestration, and policy decisions should remain outside the service boundary.
