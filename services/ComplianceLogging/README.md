# Compliance Logging Service

## Responsibility

Designed specifically for regulations.

## Examples of Regulations

- GDPR
- HIPAA
- SOC2
- ISO 27001
- PCI DSS

Stores evidence proving your organization followed required procedures.

## Examples of Compliance Events

- User accepted privacy policy
- Consent granted
- Consent withdrawn
- Customer exported data
- Customer deleted account
- MFA enabled
- Password policy changed

Unlike Audit Logs, these logs are organized around legal obligations.

## APIs

| Method | Endpoint |
|----------|------------|
| GET | `/compliance-logs` |
| POST | `/compliance-logs/search` |
| GET | `/compliance-logs/export` |
| GET | `/compliance-logs/gdpr` |
| GET | `/compliance-logs/hipaa` |
| GET | `/compliance-logs/soc2` |
| GET | `/compliance-logs/iso27001` |
| GET | `/compliance-logs/pci` |

## Example Event

```json
{
  "regulation": "GDPR",
  "event": "DATA_EXPORT",
  "user": "user123",
  "performedBy": "self",
  "timestamp": "..."
}
```