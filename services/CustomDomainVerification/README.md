# Custom Domain Verification Service

## Purpose

The Custom Domain Verification Service validates ownership of customer domains before allowing them to be attached to the platform.

This prevents unauthorized domain usage and ensures that only legitimate domain owners can configure custom domains.

Example:

User submits:

```text id="do4r3m"
portal.company.com
```

System generates:

```text id="m39fak"
TXT Record:
verify=8fj39djd83
```

The customer adds the DNS record, after which the platform verifies ownership.

---

## Responsibilities

The Custom Domain Verification Service handles:

* Domain ownership verification
* Verification token generation
* Verification status management
* Verification history tracking
* Verification retry handling
* Domain validation workflows

---

## Owns

The service owns and manages:

* Verification tokens
* Verification status
* Verification history

---

## Does NOT Own

The service does **not** own:

* DNS providers
* DNS record creation
* Domain hosting
* SSL certificates
* White-label configurations

These responsibilities belong to other services.

---

## API Endpoints

### Verification Request

```http id="cb7z4s"
POST /domain-verifications
```

### Example Response

```json id="1mz37a"
{
  "verification_token": "abc123",
  "record_type": "TXT"
}
```

### Verify Ownership

```http id="h85wvr"
POST /domain-verifications/{id}/verify
```

### Verification Status

```http id="5yxzqd"
GET /domain-verifications/{id}
```

### Reissue Token

```http id="aj4nqv"
POST /domain-verifications/{id}/regenerate
```

---

## Example Flow

```text id="f95cxa"
Customer
     ↓
Submit custom domain
     ↓
Generate TXT verification token
     ↓
Customer updates DNS
     ↓
Verification process executes
     ↓
Domain status becomes verified
```

---

## Service Interaction Notes

* Acts as a prerequisite for custom domain activation.
* Works together with DNS Automation and White-Label services.
* Supports verification retries and token regeneration.
* Maintains verification history for auditing purposes.
* Domain ownership must be confirmed before platform routing is enabled.

---

## Future Enhancements

Potential future capabilities:

* Automatic DNS record detection
* Multi-record verification methods
* Email-based domain validation
* Verification expiration policies
* Batch domain verification
* SSL pre-validation support


# DNS Automation Service

## Purpose

The DNS Automation Service automatically creates and manages DNS records through external DNS provider APIs.

Without this service:

```text id="2mf4eu"
Customer manually creates:

CNAME portal.company.com → saas.com
```

With automation:

```text id="0h8qer"
Platform automatically updates DNS records through provider APIs
```

Supported providers include:

* Cloudflare
* Route53
* Azure DNS
* Google Cloud DNS

---

## Responsibilities

The DNS Automation Service handles:

* DNS provider integrations
* DNS record management
* Automated DNS updates
* DNS synchronization jobs
* DNS health monitoring
* Provider credential management

---

## Owns

The service owns and manages:

* DNS providers
* DNS credentials
* DNS records
* DNS synchronization jobs

---

## Does NOT Own

The service does **not** own:

* Domain ownership verification
* SSL certificates
* White-label configuration
* Customer accounts
* CDN configuration

---

## API Endpoints

### Provider Management

```http id="tm5zcq"
POST /dns/providers
GET  /dns/providers
```

### DNS Record Management

```http id="g2q8wa"
POST   /dns/records
GET    /dns/records
PATCH  /dns/records/{id}
DELETE /dns/records/{id}
```

### Synchronization

```http id="j31cwz"
POST /dns/sync
```

### Health Monitoring

```http id="8l3nfw"
GET /dns/status
```

---

## Example Flow

```text id="r9y5dm"
White Label Service
         ↓
Request DNS record creation
         ↓
DNS Automation Service
         ↓
Provider API executes update
         ↓
DNS record becomes active
```

---

## Service Interaction Notes

* Integrates with external DNS provider APIs.
* Removes the need for manual DNS configuration.
* Works with Domain Verification and White-Label services.
* Synchronization jobs maintain provider consistency.
* Health checks detect propagation and configuration issues.

---

## Future Enhancements

Potential future capabilities:

* Automatic SSL provisioning
* DNS propagation tracking
* Multi-provider failover
* DNS rollback support
* Traffic routing policies
* Geographic DNS routing
