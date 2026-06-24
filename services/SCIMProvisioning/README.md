# SCIM Provisioning Service

## Responsibility
Automates user provisioning and de-provisioning from external identity providers (IdPs).

### Examples
When HR adds or removes an employee in an identity management provider (like Okta or Azure AD), SCIM automatically:
* Creates the user account
* Assigns predefined roles
* Adds appropriate tenant memberships
* Disables or deletes the account immediately when the employee leaves

## APIs

### SCIM Standard Users
* `GET    /scim/v2/Users`
* `POST   /scim/v2/Users`
* `GET    /scim/v2/Users/{id}`
* `PATCH  /scim/v2/Users/{id}`
* `DELETE /scim/v2/Users/{id}`

### SCIM Standard Groups
* `GET    /scim/v2/Groups`
* `POST   /scim/v2/Groups`
* `PATCH  /scim/v2/Groups/{id}`
* `DELETE /scim/v2/Groups/{id}`