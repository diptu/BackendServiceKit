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
- [ ] Create organization
- [ ] Update organization
- [ ] Delete organization
- [ ] Organization membership management

## 5. Role Management
- [ ] Seed default roles
- [ ] Create custom roles
- [ ] Update roles
- [ ] Delete roles
- [ ] Assign roles to users

## 6. Permission Management
- [ ] Define permissions
- [ ] Seed permission catalog
- [ ] Assign permissions to roles
- [ ] Remove permissions from roles

## 7. Authorization
- [ ] JWT validation middleware
- [ ] Role-based authorization
- [ ] Permission-based authorization
- [ ] Protect API endpoints

## 8. Audit Logging
- [ ] Login events
- [ ] Logout events
- [ ] Password changes
- [ ] Role assignments
- [ ] Permission updates

## 9. Security
- [ ] Rate limiting
- [ ] Account lockout
- [ ] Token revocation
- [ ] Input validation
- [ ] Security headers

## 10. Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] Authorization tests
- [ ] Security tests

## 11. Production Readiness
- [ ] Health checks
- [ ] Metrics endpoint
- [ ] Monitoring and alerting
- [ ] Backup and recovery

# MVP Priority

## Phase 1
- [ ] Registration
- [ ] Login
- [ ] JWT Authentication
- [ ] User CRUD
- [ ] Role CRUD
- [ ] Permission CRUD
- [ ] Authorization Middleware

## Phase 2
- [ ] Refresh Tokens
- [ ] Invitations
- [ ] Audit Logs
- [ ] Account Lockout

## Phase 3
- [ ] MFA
- [ ] SSO (OIDC/OAuth2)
- [ ] SCIM Provisioning
- [ ] ABAC Support


# Phase 4 optIonal

- [ ] Deploy on Render for free
