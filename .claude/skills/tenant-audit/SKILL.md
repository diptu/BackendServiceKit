---
name: tenant-audit
description: Verify that code handles Tenant and Org isolation.
---
# Tenant Audit Protocol
1. **Scope Check**: Does the code access any service in `/services/`?
2. **Context Injection**: Check if the service uses the `TenantContextMiddleware` from `shared/middleware/`.
3. **Query Guard**: Inspect database queries in `repositories/` to ensure they include a `tenant_id` WHERE clause.