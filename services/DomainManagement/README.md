# Domain Management Service

## Purpose

The Domain Management Service acts as the centralized source of truth for domain and subdomain management across the platform.

It stores and manages domain-related configurations used by tenants, white-label solutions, and platform routing systems.

Examples:

* tenant-a.com
* portal.tenant-a.com
* app.tenant-b.com

The service maintains domain ownership information, SSL status, and routing metadata required for traffic resolution.

---

## Responsibilities

The Domain Management Service handles:

* Domain registration management
* Subdomain management
* SSL status tracking
* Routing metadata management
* Domain ownership tracking
* Domain configuration validation
* Domain lifecycle management

---

## Owns

The service owns and manages:

* Domains
* Subdomains
* SSL status
* Routing metadata

---

## Does NOT Own

The service does **not** own:

* DNS infrastructure
* CDN configuration
* Authentication
* Tenant management
* White-label configurations

These responsibilities belong to their respective services.

---

## API Endpoints

### Domain Management

```http id="h4mv2z"
POST   /domains
GET    /domains
GET    /domains/{domain_id}
PATCH  /domains/{domain_id}
DELETE /domains/{domain_id}
```

### SSL Information

```http id="jp6r3n"
GET /domains/{domain_id}/ssl
```

### Subdomain Management

```http id="tb8x7m"
POST /domains/{domain_id}/subdomains
GET  /domains/{domain_id}/subdomains
```

---

## Example Domain Record

```json id="c7sz9a"
{
  "id": "dom_001",
  "domain": "portal.tenant-a.com",
  "type": "custom",
  "ssl_status": "active",
  "routing_target": "tenant-a",
  "status": "verified"
}
```

---

## Example Flow

```text id="53nkvj"
Tenant Administrator
         ↓
POST /domains
         ↓
Domain Validation
         ↓
SSL Verification
         ↓
Routing Metadata Stored
```

---

## Service Interaction Notes

* Serves as the authoritative source for domain configurations.
* Stores metadata used by routing and gateway systems.
* Tracks SSL status and domain verification state.
* Supports both primary domains and subdomains.
* Integrates with White-Label, CDN, Gateway, and Tenant services.

---

## Future Enhancements

Potential future capabilities:

* Automated SSL provisioning
* DNS verification workflows
* Wildcard domain support
* Multi-domain tenant support
* Domain health monitoring
* Domain expiration tracking
* Traffic routing policies
