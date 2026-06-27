---
name: dev-todos
description: Manage service-specific TODOs and aggregate them for system-wide visibility using the internal task manager.
---
# Dev-Todos Management Protocol

## 1. Storage Standards
- **Local**: Each service MUST maintain `services/<service_name>/TODO.md`.
- **Global**: The root `TODO.md` serves as the "Master Task Board."

## 2. Command Usage
- `/dev-todos --list [service_name]`: Read and display tasks from `services/[service_name]/TODO.md`.
- `/dev-todos --add "[service_name]" "[Task]"`: 
  Execute: `python scripts/todo_manager.py --add [service_name] "[Task]"`
- `/dev-todos --sync-all`: 
  Execute: `python scripts/todo_manager.py --sync`
  (Aggregates all service-level `TODO.md` files into the root `TODO.md`)

## 3. Formatting Standard
- Every entry MUST follow: `- [ ] (Status) [Scope] Task description (Due: YYYY-MM-DD)`
- **Status flags**: `[BLOCKED]`, `[IN-PROGRESS]`, `[PENDING]`, `[READY]`
- **Scope tags**: Required for multi-tenant services. Examples: `[TENANT-LEVEL]`, `[ORG-LEVEL]`, `[ABAC-POLICY]`.

## 4. Multi-Tenant Operational Notes
- **Context Verification**: Before adding a task for any service in `services/`, assess if it requires `TenantID` or `OrgID` filtering.
- **Security Scope**: If the task involves `IAM`, `Authorization`, or `TenantIsolation`, the description MUST explicitly state how the task handles the tenant boundary (e.g., "Implement XYZ filtering by TenantContext").
- **ABAC/RBAC Awareness**: When tasking `Authorization` or `AbacPolicyManagement`, ensure the description specifies the resource/user attributes involved.
- **Pre-flight Check**: Check existing `TODO.md` for duplicate logic, especially regarding existing tenant-isolation requirements.
- **Final Sync**: Perform a `--sync-all` after every major feature increment to ensure the Master Board accurately reflects the system's security posture.