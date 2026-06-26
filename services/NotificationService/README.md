# Notification Service

## Overview

The Notification Service acts as the orchestration layer for all notification workflows.

It determines:

* What notification should be sent
* Which communication channel should be used
* When a notification should be delivered
* Whether notification policies allow delivery

The service does **not** directly send messages.

Instead, it coordinates downstream delivery services.

---

## Responsibilities

The Notification Service is responsible for:

* Determining notification types
* Selecting appropriate delivery channels
* Evaluating notification policies
* Scheduling notifications
* Broadcasting notifications
* Tracking notification lifecycle status
* Retrying failed notifications
* Maintaining notification history
* Coordinating downstream delivery services

---

## Non-Responsibilities

The Notification Service should **not**:

* Deliver SMS messages directly
* Deliver emails directly
* Deliver push notifications directly
* Manage provider-specific APIs
* Handle low-level delivery mechanisms

Message transport belongs to dedicated delivery services.

---

## Downstream Services

The Notification Service delegates delivery to:

* SMS Service
* Email Service
* Push Notification Service

---

## Example Flow

### User changes password

```text id="flow701"
User Action
      │
      ▼
Password Changed Event
      │
      ▼
Notification Service
      │
 ┌────┼───────────┐
 ▼    ▼           ▼
Email Service   SMS Service   Push Service
```

The Notification Service decides:

* Which channels should receive the notification
* Whether user notification policies allow delivery
* Whether notifications should be immediate or delayed

---

## Common Use Cases

Examples of notification events:

* Account locked
* Password changed
* New tenant created
* Invoice generated

---

# API Endpoints

## Notification APIs

### Create Notification

```http id="nt011k"
POST /notifications
```

Create a notification request.

---

### Send Notification

```http id="nt723f"
POST /notifications/send
```

Trigger notification delivery immediately.

---

### Broadcast Notification

```http id="nt492a"
POST /notifications/broadcast
```

Send notifications to multiple recipients.

---

### Schedule Notification

```http id="nt184m"
POST /notifications/schedule
```

Schedule a notification for future delivery.

---

### Cancel Scheduled Notification

```http id="nt904x"
POST /notifications/cancel
```

Cancel a scheduled notification.

---

## Retrieval APIs

### Get Notification Details

```http id="nt551p"
GET /notifications/{notification_id}
```

Retrieve notification metadata and details.

---

### Get Notifications

```http id="nt288z"
GET /notifications
```

Retrieve notification records.

---

### Get Notification History

```http id="nt930r"
GET /notifications/history
```

Retrieve previously sent notifications.

---

### Get Notification Status

```http id="nt114d"
GET /notifications/status
```

Retrieve current delivery status information.

---

## Retry APIs

### Retry Failed Notification

```http id="nt445w"
POST /notifications/retry
```

Retry notification delivery after failure.

---

## High-Level Architecture

```text id="arch871"
Application Services
        │
        ▼
Notification Service
        │
 ┌──────┼──────────────┐
 ▼      ▼              ▼
SMS   Email        Push Notification
Service Service      Service
        │
        ▼
External Providers
```

---

## Notification Decision Flow

```text id="flow902"
Incoming Event
      │
      ▼
Notification Service
      │
      ├── Determine notification type
      ├── Evaluate policies
      ├── Select channels
      ├── Schedule or send
      ▼
Delivery Services
```

---

## Design Principle

The Notification Service should remain an orchestration layer:

**Event → Decision → Routing**

Delivery responsibilities belong to downstream communication services.
