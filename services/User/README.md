# User Service

## Purpose
The single service for platform identity, status lifecycle, and profile
metadata. Merges three services that were originally built separately this
session — **UserManagement**, **UserLifecycleManagement**, and
**UserProfileManagement** — into one deployable unit. See `TODO.md` for
the full rationale and what changed in the merge.

### Questions it answers
* What users exist in the platform, and what state are they in?
* What is this user's profile, preferences, avatar, and contact info?

## Responsibilities
* User identity CRUD (email, first/last name)
* Status lifecycle: `pending → active ⇄ suspended ⇄ locked → deactivated`
* Soft-delete + restore
* Platform onboarding invitations (secure, single-use, token-based)
* Profile metadata: bio, pronouns, display-name override
* Preferences: locale, timezone, freeform extras
* Avatar (URL reference only — no blob storage in this repo)
* Contact info: phone, secondary email, address

## Does NOT own
* Passwords, MFA, sessions — that's Authentication Service (separate,
  not yet built)
* Tenant memberships — that's IAM (`/api/v1/tenant-memberships`)
* Role/permission assignment — that's IAM (`/api/v1/user-roles`)
* ABAC attributes — that's IAM (`/api/v1/user-attributes`)

## Owns
* `users` (incl. `locked_reason`/`locked_by`)
* `user_status_history` (append-only audit trail of every transition)
* `user_invitations`
* `user_profiles`
* `user_preferences`
* `avatars`
* `contact_info`

## API Endpoints

### Users
```bash
POST   /api/v1/users
GET    /api/v1/users
GET    /api/v1/users/{user_id}
PATCH  /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
```

### Status lifecycle
```bash
POST /api/v1/users/{user_id}/activate
POST /api/v1/users/{user_id}/onboard      # same as activate, distinct audit action
POST /api/v1/users/{user_id}/suspend
POST /api/v1/users/{user_id}/unsuspend
POST /api/v1/users/{user_id}/lock         # body: reason, locked_by
POST /api/v1/users/{user_id}/unlock
POST /api/v1/users/{user_id}/deactivate
POST /api/v1/users/{user_id}/offboard     # same as deactivate, distinct audit action
POST /api/v1/users/{user_id}/restore      # undo a soft-delete
GET  /api/v1/users/{user_id}/status-history
```

### Platform Invitations
```bash
POST /api/v1/platform-invitations
GET  /api/v1/platform-invitations
POST /api/v1/platform-invitations/{invitation_id}/revoke
POST /api/v1/platform-invitations/accept
```

### Profile / Preferences / Avatar / Contacts
```bash
GET/PATCH        /api/v1/profiles/{user_id}
GET/PATCH        /api/v1/profiles/{user_id}/preferences
GET/POST/DELETE  /api/v1/profiles/{user_id}/avatar
GET/PATCH        /api/v1/profiles/{user_id}/contacts
```

## Architecture

```text
app/
├── main.py                     # FastAPI app factory + RabbitMQ lifespan
├── core/                       # config, logging, openapi tags
├── domain/                     # enums, exceptions, commands, events
├── models/                     # User, UserStatusHistory, UserInvitation,
│                                #   UserProfile, UserPreferences, Avatar, ContactInfo
├── repositories/                # one repo per model
├── services/                    # UserService, InvitationService,
│                                #   ProfileService, AvatarService
├── schemas/                     # Pydantic request/response models
├── api/v1/                      # users_router, invitations_router, profiles_router
└── infrastructure/
    ├── database/                # AsyncEngine, session, get_db()
    └── messaging/                # RabbitMQPublisher/NullPublisher (identity.events)
```

Publishes to RabbitMQ's `identity.events` exchange — IAM's `UserProjection`
is the intended (still-deferred) consumer.
