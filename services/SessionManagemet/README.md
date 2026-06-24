# Session Management Service

## Responsibility
Manages authenticated user sessions after successful login.

## Scope
* Create session
* Refresh session
* Revoke session
* Track active sessions
* Logout
* Force logout

## Does NOT Handle
* Password storage
* User creation
* OAuth providers

## APIs

### Session Lifecycle & Information
* `POST   /sessions`
* `GET    /sessions`
* `GET    /sessions/{session_id}`
* `DELETE /sessions/{session_id}`
* `POST   /sessions/{session_id}/refresh`
* `POST   /sessions/revoke-all`
* `GET    /sessions/me`

### User-Specific Sessions
* `GET    /users/{user_id}/sessions`
* `DELETE /users/{user_id}/sessions`