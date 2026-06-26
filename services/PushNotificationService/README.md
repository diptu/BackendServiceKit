# Push Notification Service

## Overview

The Push Notification Service is responsible only for sending push notifications to user devices. It acts as a delivery layer that abstracts communication with push notification providers across multiple platforms.

The service focuses solely on message delivery, device registration, and delivery tracking.

---

## Responsibilities

The Push Notification Service is responsible for:

* Sending push notifications
* Sending bulk notifications
* Managing device registrations
* Managing topic subscriptions
* Tracking delivery status
* Integrating with notification providers
* Exposing operational metrics

---

## Non-Responsibilities

The Push Notification Service should **not** know:

* Why the notification is being sent
* Who triggered the notification
* User preferences
* Notification policies
* Business workflows
* Authorization logic
* Campaign rules

These concerns belong to upstream services.

---

## Supported Channels

The service supports push notifications for:

* Android
* iOS
* Web Browser

---

## Supported Providers

The service delivers notifications through external providers such as:

* Firebase
* Apple Push Notification Service (APNS)

Additional providers can be added through a provider abstraction layer.

---

## Common Use Cases

Examples of notifications sent through the service:

* New comment
* Task assigned
* New login detected
* Chat message

---

# API Endpoints

## Push Delivery APIs

### Send Push Notification

```http id="pk031j"
POST /push/send
```

Send a push notification to a target device.

---

### Send Bulk Push Notification

```http id="yr094m"
POST /push/send-bulk
```

Send notifications to multiple devices.

---

## Device Management APIs

### Register Device

```http id="de942l"
POST /push/register-device
```

Register a user device and notification token.

---

### Remove Device Registration

```http id="pl283s"
DELETE /push/register-device/{device_id}
```

Remove a device registration.

---

### Get Registered Devices

```http id="kw842v"
GET /push/devices
```

Retrieve registered device information.

---

## Topic Subscription APIs

### Subscribe to Topic

```http id="tp671m"
POST /push/topics/subscribe
```

Subscribe a device to a notification topic.

Examples:

* news
* announcements
* project-updates

---

### Unsubscribe from Topic

```http id="up019v"
POST /push/topics/unsubscribe
```

Remove a device from a notification topic.

---

## Message APIs

### Get Notification Details

```http id="mg481q"
GET /push/messages/{message_id}
```

Retrieve notification metadata and details.

---

## Webhook APIs

### Delivery Status Webhook

```http id="wb921d"
POST /push/webhooks/delivery
```

Receive delivery updates from providers.

Examples:

* Delivered
* Failed
* Opened
* Rejected

---

## Metrics APIs

### Service Metrics

```http id="mx220z"
GET /push/metrics
```

Retrieve operational metrics.

Examples:

* Total notifications sent
* Delivery success rate
* Failed notifications
* Active devices
* Topic subscription counts
* Average delivery latency

---

## High-Level Flow

```text id="flow941"
Client Service
      │
      ▼
Push Notification Service
      │
      ▼
Provider Adapter Layer
      │
 ┌────┴──────────┐
 ▼               ▼
Firebase       APNS
```

---

## Design Principle

The Push Notification Service should remain a thin infrastructure service:

**Input → Delivery → Tracking**

Business logic and user-specific decisions should remain outside the service boundary.
