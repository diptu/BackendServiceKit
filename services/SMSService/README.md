# SMS Service

## Overview

The SMS Service is responsible only for sending and receiving SMS messages. It acts as a delivery layer and abstracts communication with SMS providers.

The service focuses exclusively on reliable message transport and delivery tracking.

---

## Responsibilities

The SMS Service is responsible for:

* Sending SMS messages
* Receiving inbound SMS messages
* Managing SMS provider integrations
* Tracking message delivery status
* Handling OTP generation and verification workflows
* Exposing operational metrics

---

## Non-Responsibilities

The SMS Service should **not** know:

* Why the message is being sent
* Who triggered the message
* User preferences
* Notification policies
* Business workflows
* Authorization logic
* Campaign rules

These concerns belong to upstream services.

---

## Supported Providers

The service delivers SMS messages through external providers such as:

* Twilio
* Vonage
* MessageBird

Additional providers can be added through a provider abstraction layer.

---

## Common Use Cases

Examples of messages sent through the service:

* OTP verification
* Multi-Factor Authentication (MFA) codes
* Password reset codes
* Billing alerts
* Security alerts

---

# API Endpoints

## SMS Delivery APIs

### Send SMS

```http
POST /sms/send
```

Send a single SMS message.

---

### Send Bulk SMS

```http
POST /sms/send-bulk
```

Send SMS messages to multiple recipients.

---

### Send SMS Using Template

```http
POST /sms/send-template
```

Send a message using a predefined SMS template.

---

## OTP APIs

### Send OTP

```http
POST /sms/otp/send
```

Generate and send a one-time password.

---

### Verify OTP

```http
POST /sms/otp/verify
```

Validate a previously issued OTP.

---

## Message Retrieval APIs

### Get Message Details

```http
GET /sms/messages/{message_id}
```

Retrieve message metadata and details.

---

### Get Delivery Status

```http
GET /sms/status/{message_id}
```

Retrieve delivery status for a message.

---

## Webhook APIs

### Delivery Status Webhook

```http
POST /sms/webhooks/delivery
```

Receive provider delivery updates.

Examples:

* Delivered
* Failed
* Queued
* Rejected

---

### Inbound SMS Webhook

```http
POST /sms/webhooks/inbound
```

Receive incoming SMS messages from users.

---

## Provider Management APIs

### List Providers

```http
GET /sms/providers
```

Retrieve configured SMS providers.

---

### Update Provider Configuration

```http
PUT /sms/providers/{provider_id}
```

Update provider settings or credentials.

---

## Metrics APIs

### Service Metrics

```http
GET /sms/metrics
```

Retrieve operational metrics.

Examples:

* Total messages sent
* Delivery success rate
* Failed messages
* Provider performance
* OTP success rate
* Average response latency

---

## High-Level Flow

```text
Client Service
      │
      ▼
SMS Service
      │
      ▼
Provider Adapter Layer
      │
 ┌────┴───────────┐
 ▼                ▼
Twilio        Vonage
                  ▼
             MessageBird
```

---

## Design Principle

The SMS Service should remain a thin infrastructure service:

**Input → Delivery → Tracking**

Business decisions and user-specific logic should remain outside the service boundary.
