# RBAC IAM Checklist

## 1. Project Setup
- [x] Create IAM service repository
- [x] Configure project structure
- [x] Setup environment variables
- [x] Configure logging
- [x] Setup database and migrations
- [x] Configure testing and CI/CD

## 2. Authentication
### Registration
- [x] User registration
- [x] Email uniqueness validation
- [x] Password hashing
- [x] JWT token generation

### Login
- [x] User authentication
- [x] Access token generation
- [x] Refresh token generation
- [x] Login audit logging

### Password Management
- [x] Change password
- [x] Forgot password
- [x] Password reset flow

### Federated Identity (OAuth2 / OIDC)
- [x] Configure OAuth2 state/nonce mechanism for CSRF mitigation
- [x] Implement Google login redirection endpoint
- [x] Implement Google OAuth2 backend callback handler
- [x] Extract claims from verified ID tokens and map to local RBAC user profiles

## 3. User Management
- [x] User CRUD
- [x] User profile management
- [x] User activation/deactivation
- [x] User search and filtering

## 4. Organization Management
- [x] Create organization
- [x] Update organization
- [x] Delete organization
- [x] Organization membership management

## 5. Role Management
- [x] Seed default roles
- [x] Create custom roles
- [x] Update roles
- [x] Delete roles
- [x] Assign roles to users

## 6. Permission Management
- [x] Define permissions
- [x] Seed permission catalog
- [x] Assign permissions to roles
- [x] Remove permissions from roles

## 7. Authorization
- [x] JWT validation middleware
- [x] Role-based authorization
- [x] Permission-based authorization
- [x] Protect API endpoints

## 8. Audit Logging
- [x] Login events
- [x] Logout events
- [x] Password changes
- [x] Role assignments
- [x] Permission updates

## 9. Security
- [x] Rate limiting
- [x] Account lockout
- [x] Token revocation
- [x] Input validation
- [x] Security headers

## 10. Testing
- [x] Unit tests
- [x] Integration tests
- [x] Authorization tests
- [x] Security tests

## 11. Production Readiness
- [x] Health checks
- [x] Metrics endpoint


<!-- # Phase 4 optIonal

- [ ] Deploy on Render for free -->
